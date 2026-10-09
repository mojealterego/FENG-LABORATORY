"""Controlled hardware test for Wio-E5 STM32WLE5JC AT firmware and TTN v3.

Never substitutes UART AT+MSGHEX success for a TTN network-server receipt.
LoRaWAN OTAA keys are provisioned outside this utility in the real modem.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

from .telemetry import encode_frame, parse_ttn_uplink


class FieldTestError(RuntimeError):
    pass


def _clock():
    return time.monotonic()


def issue_command(serial_port, command: str, prefix: str, timeout_s: float, clock=_clock) -> list[str]:
    """Bounded command transaction; rejects modem errors and no response."""
    if not re.fullmatch(r'AT(?:[+][A-Z0-9]+(?:[=?][A-Za-z0-9" ]+)?)?', command):
        raise FieldTestError("Unsupported AT command")
    if not 1 <= timeout_s <= 180:
        raise ValueError("Command timeout must be 1–180 seconds")
    serial_port.reset_input_buffer()
    sent = (command + "\r\n").encode("ascii")
    if serial_port.write(sent) != len(sent):
        raise FieldTestError("UART short write")
    serial_port.flush()
    deadline = clock() + timeout_s
    lines: list[str] = []
    while clock() < deadline:
        raw = serial_port.readline(256)
        if not raw:
            continue
        line = raw.decode("ascii", errors="replace").strip()
        if not line:
            continue
        lines.append(line)
        if len(lines) > 100:
            raise FieldTestError("Excessive modem response lines")
        if re.search(r"(?:ERROR|Failed|Join failed|not joined|busy)", line, flags=re.IGNORECASE):
            raise FieldTestError(f"Modem refused {command}: {line}")
        if line.startswith(prefix) and ("Done" in line or "OK" in line):
            return lines
        if prefix == "+JOIN:" and "Network joined" in line:
            # Wait for the normal +JOIN: Done end of transaction.
            continue
        if prefix in {"+DR:", "+MODE:", "+PORT:", "+AT:"} and line.startswith(prefix):
            return lines
    raise FieldTestError(f"Modem timeout waiting for {prefix}")


def run_probe(modem, *, send: bool, sample: bytes | None = None) -> dict:
    """Set EU868, Class A OTAA, port=10 and optionally transmit one frame."""
    operations = [
        ("AT", "+AT:", 5),
        ("AT+DR=EU868", "+DR:", 5),
        ("AT+MODE=LWOTAA", "+MODE:", 5),
        ("AT+PORT=10", "+PORT:", 5),
    ]
    if send:
        if sample is None or len(sample) != 8:
            raise ValueError("An eight-byte frame is required for transmission")
        operations.extend([
            ("AT+JOIN", "+JOIN:", 120),
            ('AT+MSGHEX="' + sample.hex().upper() + '"', "+MSGHEX:", 90),
        ])
    trace = []
    for command, prefix, timeout in operations:
        response = issue_command(modem, command, prefix, timeout)
        trace.append({"command": command, "response": response})
    if send:
        join_lines = trace[-2]["response"]
        if not any("Network joined" in line for line in join_lines):
            raise FieldTestError("OTAA join not confirmed")
        if not any("+MSGHEX: Done" in line for line in trace[-1]["response"]):
            raise FieldTestError("Modem did not complete uplink")
    return {
        "device": "Wio-E5 STM32WLE5JC factory AT firmware",
        "region": "EU868",
        "f_port": 10,
        "probe_state": "radio_command_completed" if send else "configured_no_transmission",
        "network_delivery": "unverified",
        "frame_hex": sample.hex().upper() if sample is not None else None,
        "trace": trace,
    }


def verify_network_receipt(path: str | Path, *, expected_payload: bytes,
                           application_id: str, device_id: str) -> dict:
    """Verify independently exported TTN v3 uplink for exact device and bytes.

    The receipt must be obtained from the actual network server, not this
    process's own output. It is not cryptographically signed by this tool.
    """
    file = Path(path)
    if file.stat().st_size > 65536:
        raise FieldTestError("TTN receipt too large")
    with file.open(encoding="utf-8") as stream:
        event = json.load(stream)
    uplink = parse_ttn_uplink(event)
    if uplink.app_id != application_id or uplink.device_id != device_id:
        raise FieldTestError("TTN identity does not match expected application/device")
    if encode_frame(
        uplink.sample.temperature_centi_c,
        uplink.sample.capacitor_mv,
        uplink.sample.teg_power_uw,
        uplink.sample.flags,
    ) != expected_payload:
        raise FieldTestError("TTN payload mismatch")
    return {
        "delivery_state": "ttn_receipt_content_matches",
        "application_id": uplink.app_id,
        "device_id": uplink.device_id,
        "frame_counter": uplink.frame_counter,
        "received_at": uplink.received_at,
        "note": "Receipt matching is independent of modem acknowledgement; archive TTN original.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wio-E5 EU868 OTAA single-uplink field test")
    parser.add_argument("--port", required=True, help="Serial port (COMx or /dev/ttyUSBx)")
    parser.add_argument("--send", action="store_true", help="Explicitly enable ONE RF transmission")
    parser.add_argument("--temperature-centic", type=int, default=4300)
    parser.add_argument("--capacitor-mv", type=int, default=3000)
    parser.add_argument("--teg-power-uw", type=int, default=-1)
    parser.add_argument("--ttn-receipt", type=Path)
    parser.add_argument("--app-id")
    parser.add_argument("--device-id")
    args = parser.parse_args(argv)
    try:
        if args.ttn_receipt is not None and (not args.app_id or not args.device_id or not args.send):
            raise FieldTestError("TTN verification needs --send --app-id --device-id")
        sample = encode_frame(
            args.temperature_centic,
            args.capacitor_mv,
            args.teg_power_uw if args.teg_power_uw >= 0 else None,
            flags=0,
        )
        try:
            import serial
        except ImportError as exc:
            raise FieldTestError("Install optional dependency: python -m pip install pyserial") from exc
        with serial.Serial(args.port, 9600, timeout=0.5, write_timeout=2) as modem:
            result = run_probe(modem, send=args.send, sample=sample)
        if args.ttn_receipt is not None:
            result["ttn"] = verify_network_receipt(
                args.ttn_receipt,
                expected_payload=sample,
                application_id=args.app_id,
                device_id=args.device_id,
            )
        result["operator_supplied_measurements"] = True
        result["tested_at_utc"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FieldTestError, ValueError, OSError) as exc:
        print(f"Fieldtest unsuccessful: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
