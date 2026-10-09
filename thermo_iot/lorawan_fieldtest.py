"""Controlled hardware test for Wio-E5 STM32WLE5JC AT firmware and TTN v3.

Never substitutes UART AT+MSGHEX success for a TTN network-server receipt.
LoRaWAN OTAA keys are provisioned outside this utility in the real modem.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import secrets
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



_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")


def build_rf_test_frame(temperature_centi_c: int, capacitor_mv: int,
                        teg_uw: int | None, *, challenge: int) -> bytes:
    """Mark UART-injected sample as LAB REFERENCE and bind a 7-bit challenge.

    The flags field reserves bit7 for reference-only telemetry. Lower 7 bits
    are an ephemeral RF test challenge in this mode (NOT a security token).
    """
    if isinstance(challenge, bool) or not isinstance(challenge, int) or not 1 <= challenge <= 127:
        raise ValueError("RF challenge must be a non-zero 7-bit integer")
    return encode_frame(temperature_centi_c, capacitor_mv, teg_uw,
                        flags=0x80 | challenge)


def _utc_datetime(value: str | datetime) -> datetime:
    if isinstance(value, str):
        if not _RFC3339.fullmatch(value):
            raise FieldTestError("Expected an RFC3339 UTC timestamp")
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise FieldTestError("Invalid timestamp") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise FieldTestError("Timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


def _utc_stamp(value: str | datetime) -> str:
    return _utc_datetime(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _read_json_file(path: str | Path) -> dict:
    file = Path(path)
    if file.stat().st_size > 65536:
        raise FieldTestError("Evidence JSON file exceeds 64 KiB")
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:
                raise FieldTestError("Repeated JSON object key")
            result[key]=value
        return result
    def invalid_constant(value):
        raise FieldTestError("Non-finite JSON constant")
    try:
        with file.open(encoding="utf-8") as stream:
            result=json.load(stream, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise FieldTestError("Malformed evidence JSON") from exc
    if not isinstance(result, dict):
        raise FieldTestError("Evidence file must be a JSON object")
    return result


def record_rf_attempt(path: str | Path, *, modem_result: dict, payload: bytes,
                      application_id: str, device_id: str,
                      start_utc: str | datetime, end_utc: str | datetime) -> dict:
    """Create private, never-overwritten operator evidence AFTER radio command.

    The saved report is an RF command record, not proof of radio transmission
    or network reception. The user must provide the independent TTN export.
    """
    if not _ID.fullmatch(application_id) or not _ID.fullmatch(device_id):
        raise FieldTestError("Invalid TTN application/device identity")
    if not isinstance(payload, bytes) or len(payload)!=8 or not (payload[-1] & 0x80) or not (payload[-1] & 0x7f):
        raise FieldTestError("Radio reference frame with a non-zero challenge is required")
    if (modem_result.get("network_delivery")!="unverified"
            or modem_result.get("probe_state")!="radio_command_completed"):
        raise FieldTestError("Radio command completion is required to record an attempt")
    start=_utc_datetime(start_utc)
    end=_utc_datetime(end_utc)
    if end < start or end-start>timedelta(minutes=10):
        raise FieldTestError("Invalid radio command time window")
    data={
        "schema":"thermo-iot-rf-attempt/v1",
        "owner":"Mojeaterego - Andrzej Mikulski",
        "rights":"Copyright (c) 2026 Mojeaterego - Andrzej Mikulski. All rights reserved.",
        "evidence_type":"operator_uart_command",
        "verification_state":"pending_external_ttn_receipt",
        "application_id":application_id,
        "device_id":device_id,
        "payload_hex":payload.hex().upper(),
        "challenge_7bit":payload[-1] & 0x7f,
        "command_started_utc":_utc_stamp(start),
        "command_finished_utc":_utc_stamp(end),
        "note":"AT+MSGHEX Done is NOT LoRaWAN network delivery. Archive an independent TTN uplink.",
    }
    # Create with atomic no-clobber permissions, including on multi-user hosts.
    fd=os.open(Path(path),os.O_WRONLY | os.O_CREAT | os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as fp:
            json.dump(data,fp,ensure_ascii=False,indent=2)
            fp.write("\n")
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
    return data


def verify_recorded_attempt(attempt_path: str | Path, receipt_path: str | Path) -> dict:
    """Verify a TTN export obtained *after* the locally recorded RF command.

    This validates file consistency, not authenticity of a user-supplied TTN
    JSON, the instrument clock, or cryptographic LoRaWAN network integrity.
    """
    report=_read_json_file(attempt_path)
    required={
        "schema","evidence_type","verification_state","application_id","device_id",
        "payload_hex","challenge_7bit","command_started_utc","command_finished_utc"
    }
    if not required.issubset(report):
        raise FieldTestError("Incomplete RF attempt report")
    if (report["schema"]!="thermo-iot-rf-attempt/v1"
        or report["evidence_type"]!="operator_uart_command"
        or report["verification_state"]!="pending_external_ttn_receipt"):
        raise FieldTestError("Report must represent an unverified UART command attempt")
    hexdump=report["payload_hex"]
    if (not isinstance(hexdump,str) or not re.fullmatch(r"[0-9A-F]{16}",hexdump)
        or not isinstance(report["challenge_7bit"],int)
        or isinstance(report["challenge_7bit"],bool)):
        raise FieldTestError("Invalid RF challenge/payload in record")
    payload=bytes.fromhex(hexdump)
    if not payload[-1]&0x80 or (payload[-1]&0x7f)!=report["challenge_7bit"] or not (payload[-1]&0x7f):
        raise FieldTestError("RF challenge does not match frame flags")
    start=_utc_datetime(report["command_started_utc"])
    end=_utc_datetime(report["command_finished_utc"])
    if end<start or end-start>timedelta(minutes=10):
        raise FieldTestError("Invalid radio attempt interval")
    event=_read_json_file(receipt_path)
    uplink=parse_ttn_uplink(event)
    if uplink.app_id!=report["application_id"] or uplink.device_id!=report["device_id"]:
        raise FieldTestError("TTN uplink identity differs from transmission attempt")
    decoded=encode_frame(
        uplink.sample.temperature_centi_c, uplink.sample.capacitor_mv,
        uplink.sample.teg_power_uw, uplink.sample.flags,
    )
    if decoded!=payload:
        raise FieldTestError("TTN uplink payload or ephemeral challenge mismatch")
    received=_utc_datetime(uplink.received_at)
    if received < start or received > end+timedelta(minutes=5):
        raise FieldTestError("TTN receipt timestamp not within recorded send window")
    return {
        "delivery_state":"ttn_receipt_content_matches",
        "frame_counter":uplink.frame_counter,
        "session_key_id_present":True,
        "received_at":uplink.received_at,
        "challenge_7bit":report["challenge_7bit"],
        "application_id":uplink.app_id,
        "device_id":uplink.device_id,
        "evidence_warning":"Matching is a content+clock consistency check of an operator-provided external TTN JSON, NOT cryptographic attestation; retain original network event and instrument/clock records.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wio-E5 EU868 OTAA single-uplink field test and two-stage TTN verification")
    parser.add_argument("--port",help="Serial port (COMx or /dev/ttyUSBx). Not used for offline verification")
    parser.add_argument("--send",action="store_true",help="Explicitly enable one radio uplink")
    parser.add_argument("--report",type=Path,help="NEW operator RF attempt report, never overwritten")
    parser.add_argument("--verify-report",type=Path,help="Previously created RF attempt report")
    parser.add_argument("--ttn-receipt",type=Path,help="Independent TTN export for offline verification mode")
    parser.add_argument("--app-id",help="Expected TTN application ID, required with --report")
    parser.add_argument("--device-id",help="Expected TTN device ID, required with --report")
    parser.add_argument("--temperature-centic",type=int,default=4300)
    parser.add_argument("--capacitor-mv",type=int,default=3000)
    parser.add_argument("--teg-power-uw",type=int,default=-1)
    args=parser.parse_args(argv)
    try:
        if args.verify_report is not None or args.ttn_receipt is not None:
            if (args.verify_report is None or args.ttn_receipt is None
                or args.port or args.send or args.report or args.app_id or args.device_id):
                raise FieldTestError("Offline verification needs only --verify-report PATH --ttn-receipt PATH")
            print(json.dumps(verify_recorded_attempt(args.verify_report,args.ttn_receipt),
                             indent=2,ensure_ascii=False))
            return 0
        if not args.port:
            raise FieldTestError("--port is required for hardware commands")
        if args.report is not None and (not args.send or not args.app_id or not args.device_id):
            raise FieldTestError("RF report requires --send --app-id --device-id")
        if args.report is not None and args.report.exists():
            raise FieldTestError("Report file already exists: will not transmit and overwrite")
        challenge=secrets.randbelow(127)+1
        sample=build_rf_test_frame(
            args.temperature_centic,args.capacitor_mv,
            args.teg_power_uw if args.teg_power_uw>=0 else None,challenge=challenge,
        )
        try:
            import serial
        except ImportError as exc:
            raise FieldTestError("Install pyserial (python -m pip install pyserial)") from exc
        start=datetime.now(timezone.utc)
        with serial.Serial(args.port,9600,timeout=0.5,write_timeout=2) as modem:
            result=run_probe(modem,send=args.send,sample=sample)
        end=datetime.now(timezone.utc)
        if args.report is not None:
            record=record_rf_attempt(
                args.report,modem_result=result,payload=sample,
                application_id=args.app_id,device_id=args.device_id,
                start_utc=start,end_utc=end,
            )
            result["report_file"]=str(args.report)
            result["verification_state"]=record["verification_state"]
        result["operator_supplied_measurements"]=True
        result["reference_only"]=True
        result["challenge_7bit"]=challenge
        result["tested_at_utc"]=_utc_stamp(end)
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (OSError,FieldTestError,ValueError) as exc:
        print(f"Fieldtest unsuccessful: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
