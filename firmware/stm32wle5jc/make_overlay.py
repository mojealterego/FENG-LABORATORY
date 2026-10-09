"""STM32CubeIDE application overlay generator for Seeed Wio-E5 STM32WLE5JC.

The native LoRaWAN MAC, radio BSP, HAL and linker script belong to the vendor
project. This tool stages a fixed eight-byte integration-test payload, without
claiming pipe temperature, TEG harvesting or successful over-the-air tests.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = Path("Projects/Applications/LoRaWAN/LoRaWAN_End_Node/LoRaWAN/App")
START = "static void SendTxData(void)\n{"
FINISH = "\nstatic void OnTxTimerEvent(void *context)"
NEW_SEND = r"""static void SendTxData(void)
{
  /* RF integration mode: MCU die temp only, NO pipe sensor or energy monitor.
   * 0 mV = unavailable capacitor; -1 uW = no TEG measurement;
   * diagnostic flags 0x80 = deliberate reference/test data.
   */
  UTIL_TIMER_Time_t nextTxIn = 0;
  int32_t die_temp_centi_c = ((int32_t)(SYS_GetTemperatureLevel() >> 8)) * 100;
  uint8_t frame[THERMO_IOT_FRAME_LEN];
  uint32_t index;

  if (!thermo_iot_encode_frame(die_temp_centi_c, 0u, -1, 0x80u, frame))
  {
    APP_LOG(TS_OFF, VLEVEL_M, "Thermo-IoT frame invalid\r\n");
    return;
  }
  for (index = 0u; index < THERMO_IOT_FRAME_LEN; ++index)
  {
    AppData.Buffer[index] = frame[index];
  }
  AppData.Port = LORAWAN_USER_APP_PORT;
  AppData.BufferSize = THERMO_IOT_FRAME_LEN;
  if (LmHandlerSend(&AppData, LORAWAN_DEFAULT_CONFIRMED_MSG_STATE,
                    &nextTxIn, false) == LORAMAC_HANDLER_SUCCESS)
  {
    APP_LOG(TS_ON, VLEVEL_L, "Thermo-IoT uplink queued\r\n");
  }
  else
  {
    APP_LOG(TS_ON, VLEVEL_L, "Thermo-IoT queue refused, retry no earlier than %lu ms\r\n",
            (unsigned long)nextTxIn);
  }
}
"""


class IntegrationError(ValueError):
    pass


def rewrite_app(source: str) -> str:
    if '#include "thermo_iot_frame.h"' in source:
        raise IntegrationError("Application has already been overlaid")
    if source.count('#include "lora_app.h"\n') != 1 or source.count(START) != 1:
        raise IntegrationError("Vendor source layout is not recognized")
    start = source.index(START)
    end = source.find(FINISH, start)
    if end < start:
        raise IntegrationError("SendTxData end marker not found")
    original = source[start:end]
    if "LmHandlerSend(" not in original or "AppData.BufferSize" not in original:
        raise IntegrationError("The vendor SendTxData signature changed")
    return (source[:start] + NEW_SEND + source[end:]).replace(
        '#include "lora_app.h"\n',
        '#include "lora_app.h"\n#include "thermo_iot_frame.h"\n', 1
    )


def rewrite_header(source: str) -> str:
    for pattern, replacement in (
        (r"(?m)^(#define APP_TX_DUTYCYCLE\s+)\d+\s*$", r"\g<1>600000"),
        (r"(?m)^(#define LORAWAN_USER_APP_PORT\s+)\d+\s*$", r"\g<1>10"),
    ):
        source, changed = re.subn(pattern, replacement, source)
        if changed != 1:
            raise IntegrationError("Expected Seeed LoRaWAN application macro missing")
    if "LORAMAC_REGION_EU868" not in source or "ACTIVATION_TYPE_OTAA" not in source:
        raise IntegrationError("EU868 and OTAA must be the target configuration")
    return source


def prepare_overlay(vendor_root: Path, output_root: Path) -> dict:
    vendor_app = vendor_root / APP_DIR
    if not vendor_app.is_dir():
        raise IntegrationError("Missing Seeed LoRaWAN_End_Node project")
    app = rewrite_app((vendor_app / "lora_app.c").read_text(encoding="utf-8"))
    hdr = rewrite_header((vendor_app / "lora_app.h").read_text(encoding="utf-8"))
    content = {
        "lora_app.c": app,
        "lora_app.h": hdr,
        "thermo_iot_frame.c": (ROOT / "firmware/src/thermo_iot_frame.c").read_text(encoding="utf-8"),
        "thermo_iot_frame.h": (ROOT / "firmware/include/thermo_iot_frame.h").read_text(encoding="utf-8"),
    }
    if output_root.exists():
        raise FileExistsError("Output already exists: will not overwrite code")
    output_root.mkdir(parents=True)
    for name, value in content.items():
        (output_root / name).write_text(value, encoding="utf-8")
    return {
        "staged_files": sorted(content),
        "region": "EU868",
        "activation": "OTAA",
        "period_ms": 600000,
        "fport": 10,
        "payload": "Thermo-IoT v1 8 bytes: MCU DIE temperature, capacitor unavailable (0), TEG unavailable (65535), flags 0x80",
        "cross_compiled": False,
        "rf_transmission_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage a no-overwrite Seeed Wio-E5 LoRaWAN overlay")
    parser.add_argument("--vendor-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_overlay(args.vendor_root, args.output_dir)
    except (OSError, IntegrationError) as exc:
        print(f"Overlay refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
