"""Generate a visibly synthetic dataset in a NEW local SQLite database only.

No real network, hardware or LoRaWAN keys are used. Existing data is protected
by the atomic O_EXCL creation of a dedicated demonstration database.
"""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import sys

from .telemetry import TelemetryService, TelemetryStore, encode_frame


APP_ID = "thermo-iot-demo"
DEVICE_ID = "synthetic-pipe-01"
SESSION_ID = "SYNTHETIC-SESSION-DO-NOT-USE"


def generate_demo(path: str | Path, *, count: int = 144) -> dict:
    if isinstance(count, bool) or not isinstance(count, int) or not 6 <= count <= 5000:
        raise ValueError("Demo point count must be an integer from 6 to 5000")
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    service = TelemetryService(TelemetryStore(file))
    base_time = datetime(2026, 10, 1, tzinfo=timezone.utc)
    anomaly_index = count // 2
    for i in range(count):
        temp_centi_c = 4300 + round(90 * math.sin(i / 10.0))
        if i == anomaly_index:
            temp_centi_c += 1100
        voltage_mv = 2700 + round(70 * math.sin(i / 15.0))
        teg_power_uw = 80 + round(15 * (1 + math.sin(i / 8.0)))
        frame = encode_frame(temp_centi_c, voltage_mv, teg_power_uw, flags=0)
        timestamp = (base_time + timedelta(minutes=10 * i)).isoformat().replace("+00:00", "Z")
        sample = {
            "end_device_ids": {
                "device_id": DEVICE_ID,
                "application_ids": {"application_id": APP_ID},
            },
            "received_at": timestamp,
            "uplink_message": {
                "session_key_id": SESSION_ID,
                "f_cnt": i + 1,
                "f_port": 10,
                "frm_payload": base64.b64encode(frame).decode("ascii"),
            },
        }
        service.process(sample)
    summary = service.store.summary(APP_ID, DEVICE_ID)
    return {
        "evidence_type": "synthetic",
        "generated": count,
        "application_id": APP_ID,
        "device_id": DEVICE_ID,
        "candidate_anomalies": summary["candidate_anomalies"],
        "note": "Synthetic demonstration. No actual IoT device, leak or environmental reading.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a new synthetic Thermo-IoT dashboard database")
    parser.add_argument("--db", required=True, help="New SQLite path: existing files are never overwritten")
    parser.add_argument("--count", type=int, default=144)
    args = parser.parse_args(argv)
    try:
        outcome = generate_demo(args.db, count=args.count)
    except (OSError, ValueError) as exc:
        print(f"Demo generation refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(outcome, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
