"""Offline, bounded The Things Stack v3 LoRaWAN field-quality inspection.

Receipts and counters in user-provided JSONL cannot establish transmission
reliability, cryptographic authenticity, calibration or physical autonomy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Mapping, Sequence

from .telemetry import UplinkValidationError, parse_ttn_uplink

MAX_JSONL_BYTES = 8_000_000
MAX_EVENTS = 10_000
MAX_LINE_BYTES = 65536


class RfAuditError(ValueError):
    """Malformed or unreliable application-layer radio export."""


def _pairs(items):
    output = {}
    for k,v in items:
        if k in output:
            raise RfAuditError("Duplicate JSON keys in TTN export")
        output[k] = v
    return output


def _constant(value):
    raise RfAuditError("Non-finite numeric JSON value")


def read_ttn_jsonl(source: str | Path, *, max_bytes: int = MAX_JSONL_BYTES) -> list[dict]:
    """Read at most MAX_EVENTS standalone TTS event objects from an export."""
    if not isinstance(max_bytes,int) or isinstance(max_bytes,bool) or not 1<=max_bytes<=MAX_JSONL_BYTES:
        raise ValueError("Invalid maximum file size")
    path=Path(source)
    if path.stat().st_size > max_bytes:
        raise RfAuditError("TTN JSONL export exceeds allowed file size")
    events=[]
    with path.open("rb") as fp:
        for number,raw in enumerate(fp,1):
            if number>MAX_EVENTS:
                raise RfAuditError("TTN export exceeds 10000 events")
            if len(raw)>MAX_LINE_BYTES:
                raise RfAuditError("TTN JSONL line is too large")
            if not raw.strip():
                raise RfAuditError("Blank line in TTN export")
            try:
                decoded=json.loads(
                    raw.decode("utf-8"),object_pairs_hook=_pairs,
                    parse_constant=_constant,
                )
            except (ValueError, UnicodeError) as exc:
                if isinstance(exc,RfAuditError):
                    raise
                raise RfAuditError("Invalid JSONL event") from exc
            if not isinstance(decoded,dict):
                raise RfAuditError("TTN JSONL event must be an object")
            events.append(decoded)
    if not events:
        raise RfAuditError("TTN export is empty")
    return events


def _timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)
    except (ValueError,TypeError) as exc:
        raise RfAuditError("Invalid normalized uplink timestamp") from exc


def _radio_value(value: object,label:str,lo:float,hi:float) -> float:
    if isinstance(value,bool) or not isinstance(value,(float,int)):
        raise RfAuditError(f"Invalid {label} type")
    parsed=float(value)
    if not math.isfinite(parsed) or not lo<=parsed<=hi:
        raise RfAuditError(f"Invalid {label} value")
    return parsed


def _rx_observations(event: Mapping) -> tuple[float|None,float|None]:
    message=event["uplink_message"]
    metadata=message.get("rx_metadata",[])
    if not isinstance(metadata,list) or len(metadata)>32:
        raise RfAuditError("Malformed or oversized rx_metadata")
    if not metadata:
        return None,None
    rssi=[]
    snr=[]
    for item in metadata:
        if not isinstance(item,Mapping):
            raise RfAuditError("rx_metadata item must be an object")
        if "rssi" in item:
            rssi.append(_radio_value(item["rssi"],"RSSI dBm",-200,30))
        if "snr" in item:
            snr.append(_radio_value(item["snr"],"SNR dB",-50,50))
    # Using the best available gateway value for each uplink. This is
    # descriptive, not representative of all environments/gateways.
    return max(rssi) if rssi else None,max(snr) if snr else None


def analyze_events(
    events: Sequence[Mapping], *,
    expected_app: str,
    expected_device: str,
) -> dict:
    if not isinstance(events,(list,tuple)) or not 1<=len(events)<=MAX_EVENTS:
        raise RfAuditError("Provide 1..10000 TTN uplinks")
    if not isinstance(expected_app,str) or not isinstance(expected_device,str):
        raise RfAuditError("Expected application/device identifiers required")
    unique={}
    duplicates=0
    for event in events:
        try:
            uplink=parse_ttn_uplink(event)
        except (UplinkValidationError,AttributeError,KeyError,TypeError) as exc:
            raise RfAuditError("Invalid TTN LoRaWAN application uplink") from exc
        if (uplink.app_id,uplink.device_id)!=(expected_app,expected_device):
            raise RfAuditError("Unexpected application or device in TTN export")
        stamp=_timestamp(uplink.received_at)
        rssi,snr=_rx_observations(event)
        key=(uplink.session_key_id,uplink.frame_counter)
        if key in unique:
            previous=unique[key][0]
            if previous.sample != uplink.sample:
                raise RfAuditError("Conflicting repeated FCnt and session")
            duplicates+=1
            continue
        unique[key]=(uplink,stamp,rssi,snr)
    ordered=sorted(unique.values(),key=lambda item:(item[1],item[0].frame_counter))
    refs=sum(1 for uplink,*_ in ordered if uplink.sample.flags & 0x80)
    sessions={}
    for record in ordered:
        uplink=record[0]
        sessions.setdefault(uplink.session_key_id,[]).append(record)
    discontinuities=0
    regressions=0
    for sequence in sessions.values():
        before=None
        for uplink,*_ in sequence:
            if before is not None:
                if uplink.frame_counter < before:
                    regressions+=1
                elif uplink.frame_counter > before+1:
                    discontinuities+=uplink.frame_counter-before-1
            before=uplink.frame_counter
    times=[record[1] for record in ordered]
    gaps=[(curr-prev).total_seconds() for prev,curr in zip(times,times[1:])]
    signal=[r[2] for r in ordered if r[2] is not None]
    noise=[r[3] for r in ordered if r[3] is not None]
    return {
        "application_id":expected_app,
        "device_id":expected_device,
        "received_events":len(events),
        "unique_uplinks":len(ordered),
        "duplicate_events":duplicates,
        "observed_sessions":len(sessions),
        "reference_lab_frames":refs,
        "pipe_measurement_frames":len(ordered)-refs,
        "counter_discontinuity_estimate":discontinuities,
        "counter_regressions":regressions,
        "observed_duration_s":(times[-1]-times[0]).total_seconds(),
        "median_observed_gap_s":statistics.median(gaps) if gaps else None,
        "maximum_observed_gap_s":max(gaps) if gaps else None,
        "median_rssi_dbm":statistics.median(signal) if signal else None,
        "median_snr_db":statistics.median(noise) if noise else None,
        "rssi_samples":len(signal),
        "snr_samples":len(noise),
        "rf_delivery_rate":"not_estimable_from_received_packets_only",
        "physical_reception_verified":False,
        "provenance":"independent human/network-server authentication required",
        "interpretation":(
            "Counter discontinuities are NOT a measured packet loss rate. "
            "Unseen joins, MAC frames, retries, reboots, loss of power and "
            "counter persistence are not inferable from received application "
            "payloads. JSONL contents may be synthetic or forged."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description="Analyze private The Things Stack JSONL RF uplinks")
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--app-id",required=True)
    p.add_argument("--device-id",required=True)
    args=p.parse_args(argv)
    try:
        report=analyze_events(
            read_ttn_jsonl(args.file),
            expected_app=args.app_id,expected_device=args.device_id,
        )
    except (OSError,ValueError) as exc:
        print(f"RF audit failed: {exc}",file=sys.stderr)
        return 2
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
