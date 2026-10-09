"""Explicitly operated SCPI DMM voltage/current captures for thermogenerator I-V.

The operator switches resistors/thermal settings by hand. SCPI instrument
readback is evidence of an instrument measurement, not calibration, accurate
source temperature, time synchronization or actual connected TEG hardware.
"""
import argparse
from datetime import datetime, timezone
import csv
import json
import math
from pathlib import Path
import re
import sys
from typing import Protocol


class Meter(Protocol):
    def query(self, command: str) -> str:
        ...


class MeterError(RuntimeError):
    pass


def finite_measurement(text: str, label: str, maximum: float) -> float:
    try:
        value = float(text.strip())
    except (AttributeError, ValueError, TypeError) as exc:
        raise MeterError(f"Invalid {label} instrument reading") from exc
    if not math.isfinite(value) or value < 0 or value > maximum:
        raise MeterError(f"{label} reading out of expected 0..{maximum} range")
    return value


def capture_sweep(
    voltmeter: Meter, ammeter: Meter,
    *,
    run_id: str,
    resistances_ohm: list[float],
    hot_c: float,
    cold_c: float,
    confirm=None,
    now=None,
) -> list[dict[str, str]]:
    """Interactive single-pass load sweep, one SCPI pair per resistor step.

    Readings are sequential, not simultaneous. Contact resistance and ammeter
    burden voltage must be independently characterized. This code does not
    autonomously apply loads or control external power supplies.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_id):
        raise ValueError("Invalid run identifier")
    if len(resistances_ohm) < 3 or len(resistances_ohm) > 100:
        raise ValueError("At least three and at most 100 load points are required")
    for resistance in resistances_ohm:
        if not math.isfinite(resistance) or resistance <= 0:
            raise ValueError("All resistances must be positive and finite")
    if not all(math.isfinite(x) for x in (hot_c, cold_c)) or not (-50 <= cold_c < hot_c <= 200):
        raise ValueError("Hot and cold face temperatures must satisfy -50 <= cold < hot <= 200 C")
    if confirm is None:
        def confirm(resistance):
            entered = input(f"Install {resistance:g} ohm load, stabilize ΔT, then type READY: ")
            if entered.strip() != "READY":
                raise MeterError("Operator cancelled this load point")
    if now is None:
        def now():
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = []
    for load in resistances_ohm:
        confirm(load)
        v = finite_measurement(voltmeter.query("MEAS:VOLT:DC?"), "DC voltage [V]", 20)
        i = finite_measurement(ammeter.query("MEAS:CURR:DC?"), "DC current [A]", 5)
        records.append({
            "run_id": run_id,
            "measurement_utc": now(),
            "hot_c": f"{hot_c:.3f}",
            "cold_c": f"{cold_c:.3f}",
            "voltage_mv": f"{v * 1000:.9g}",
            "current_ma": f"{i * 1000:.9g}",
            "evidence_type": "measured",
        })
    return records


def store_records(path: str | Path, records: list[dict[str, str]]) -> None:
    """Exclusive creation; never overwrite prior measured or synthetic data."""
    if not records:
        raise ValueError("No readings to record")
    names = ["run_id", "measurement_utc", "hot_c", "cold_c",
             "voltage_mv", "current_ma", "evidence_type"]
    with Path(path).open("x", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=names, extrasaction="raise")
        writer.writeheader()
        writer.writerows(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manually supervised real SCPI thermogenerator I-V sweep")
    parser.add_argument("--voltmeter", required=True, help="VISA resource address for DC voltmeter")
    parser.add_argument("--ammeter", required=True, help="VISA resource address for DC ammeter")
    parser.add_argument("--loads-ohm", required=True, help="Three or more comma-separated resistor values")
    parser.add_argument("--hot-c", required=True, type=float, help="Operator logged TEG hot-side temperature")
    parser.add_argument("--cold-c", required=True, type=float, help="Operator logged TEG cold-side temperature")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        loads = [float(text.strip()) for text in args.loads_ohm.split(",")]
        if args.voltmeter == args.ammeter:
            raise ValueError("Two independent instrument VISA resources are required")
        if args.output.exists():
            raise FileExistsError("Output exists; measurement files are append-protected")
        try:
            import pyvisa
        except ImportError as exc:
            raise MeterError("Install instrument dependency: python -m pip install pyvisa pyvisa-py") from exc
        with pyvisa.ResourceManager("@py") as rm:
            with rm.open_resource(args.voltmeter) as vm, rm.open_resource(args.ammeter) as am:
                readings = capture_sweep(
                    vm, am, run_id=args.run_id, resistances_ohm=loads,
                    hot_c=args.hot_c, cold_c=args.cold_c,
                )
        store_records(args.output, readings)
        print(json.dumps({
            "evidence_type": "measured",
            "electrical_source": "SCPI instrument responses",
            "temperature_source": "operator supplied",
            "simultaneous_sample": False,
            "output": str(args.output),
            "samples": len(readings),
            "warning": "Calibration/thermal stability/current burden unverified by this tool",
        }, indent=2))
        return 0
    except (OSError, ValueError, MeterError, KeyboardInterrupt) as exc:
        print(f"SCPI capture not completed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
