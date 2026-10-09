# STM32WLE5JC / Seeed LoRaWAN End Node — native RF integration

This directory contains a **non-destructive four-file source overlay** for Seeed Studio's official STM32CubeIDE application. It uses the actual STM32WLE5JC LoRaWAN MAC and radio middleware from the vendor project, rather than creating a proprietary, incomplete "LoRaWAN stack".

**Upstream checked on 2026-10-09:** `Seeed-Studio/LoRaWan-E5-Node`, `main` at `163c05379b1805dd8f2c061d4557a69985acc953`. The exact SendTxData, APP_TX_DUTYCYCLE, LORAWAN_USER_APP_PORT, EU868, OTAA anchors were inspected. Recheck any newer vendor SDK release. https://github.com/Seeed-Studio/LoRaWan-E5-Node

## Staging — work on a workstation with STM32CubeIDE and an ST-LINK

```sh
git clone https://github.com/Seeed-Studio/LoRaWan-E5-Node.git
python -m firmware.stm32wle5jc.make_overlay \
  --vendor-root ./LoRaWan-E5-Node \
  --output-dir ./local-build/thermo-wio-e5-overlay
```

The four files in `local-build/thermo-wio-e5-overlay/` are `lora_app.c`, `lora_app.h`, `thermo_iot_frame.c`, `thermo_iot_frame.h`. Copy them to an **isolated copy** of `Projects/Applications/LoRaWAN/LoRaWAN_End_Node/LoRaWAN/App` and allow STM32CubeIDE to include the extra C file in its managed build. This script refuses to replace existing staging output and does not touch the upstream tree. Add real OTAA identifiers/keys via the vendor-prescribed secure provisioning procedure — never commit secrets.

The test profile sends **port 10** after the library joins via OTAA, with nominal spacing **10 minutes**. Payload fields: MCU *internal die* temperature `temp_centi`, `capacitor_mv=0` (unavailable), `teg_power_uw=65535` (unavailable) and `flags=0x80` (reference). The backend segregates these events as `reference_telemetry` so they do not train the pipeline on wrong process temperatures. This is for RF integration only — it is **not** a complete batteryless field sensor, nor a calibrated pipe temperature channel.

## Verified vs unverified

GitHub Actions uses the available Clang ARM target to cross-compile `thermo_iot_frame.c`, `thermo_iot_power_policy.c` and `thermo_iot_app.c` as **ARM EABI5 Cortex-M4 relocatable objects**, with `-ffreestanding -Wall -Wextra -Werror`. Host C11 and Python tests also run. This is a meaningful target-architecture syntax check, **not** a full linked STM32 firmware image.

**Not yet performed:** STM32CubeIDE cross-link with Seeed middleware, startup/interrupts/RTC, actual flash to Wio-E5, on-device HAL sensor/ADC integration, LoRaWAN link margin measurement, TTN gateway receipt, and autonomous TEG power validation. No test in this repository implies those physical achievements.

## Acceptance package required for flashing and field work

- A reproducible CubeIDE build log, `.elf`, `.map`, `.hex`, source/vendor commit IDs, compiler version and FLASH/RAM report.
- ST-LINK programming and boot log, board revision and pin mapping; properly selected antenna for EU868.
- TTN *independent* real receipt containing fCnt, port 10, payload, RSSI/SNR and received_at.
- Explicit energy audit including join/reset cost, RF current pulses, capacitor voltage sag, cold-start and real PMIC/TEG data.

For bench radio AT firmware instead of overwriting the MCU, use `python -m thermo_iot.lorawan_fieldtest`.

## Complete GNU ARM RF reference image — confirmed build 2026-10-09

The pinned Seeed STM32WLE5JCIx project was compiled and linked in CI to `thermo_wio_e5_rf_reference.elf`, `.hex`, `.map` using `build_cube_gcc.py`. [Verified build](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37956017016) · [download archived binaries](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37956017016/artifacts/11627633166).

Command (requires GNU Arm Embedded toolchain and official Seeed source at the pinned commit):

```sh
python -m firmware.stm32wle5jc.build_cube_gcc --vendor-root ./LoRaWan-E5-Node --output-dir ./local-build/wio-e5
```

The upstream 84+ C source files are selected through actual Eclipse `.project` links and `.cproject` Debug compiler symbols. Startup and STM32WLE5JC linker script are included. The HEX SHA256 at the verified CI run was `e9a3d1df50e8c5a0eb3a52d03a78ce236c72ead47e3924e0c9d1b1b63d66a4ea`. FLASH region used 63,564 bytes / 256 KiB.

**Lab RF reference image only. Do not flash into a district-heating field device.** No MCU SWD flash, RTOS/RTC power profiling, custom temperature sensor, PMIC ADC and supercapacitor ADC, validated energy scheduler, actual OTAA credentials, radio/antenna or gateway receipt have been proven.
