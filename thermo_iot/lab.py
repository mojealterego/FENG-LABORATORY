"""TEG current/voltage sweep analysis with explicit evidence provenance.

No conversion to TRL, PMIC input power or installed usable power is inferred:
a sampled I-V peak is only the best observed load point in that sweep.
"""

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from statistics import median
import sys


REQUIRED_COLUMNS = (
    "run_id", "measurement_utc", "hot_c", "cold_c",
    "voltage_mv", "current_ma", "evidence_type",
)
DEFAULT_MAX_CSV_BYTES = 5_000_000


class LabValidationError(ValueError):
    """Invalid, incomplete or mixed-origin bench data."""


@dataclass(frozen=True)
class BenchReading:
    run_id: str
    measurement_utc: str
    hot_c: float
    cold_c: float
    voltage_mv: float
    current_ma: float
    evidence_type: str

    @property
    def delta_t_k(self) -> float:
        return self.hot_c - self.cold_c

    @property
    def power_w(self) -> float:
        return self.voltage_mv * self.current_ma * 1e-6


@dataclass(frozen=True)
class SweepResult:
    run_id: str
    point_count: int
    median_delta_t_k: float
    delta_t_span_k: float
    observed_peak_power_w: float
    voltage_at_peak_mv: float
    current_at_peak_ma: float
    thermal_drift_warning: bool


@dataclass(frozen=True)
class LabReport:
    evidence_type: str
    run_count: int
    median_observed_peak_power_w: float
    runs: tuple[SweepResult, ...]
    note: str = (
        "Observed sweep values only. No calibration, TEG-to-PMIC power "
        "delivery, cold-start, service life or TRL is proven by this report."
    )

    def to_dict(self) -> dict:
        return asdict(self)


def _finite_float(value: str | None, label: str, minimum: float, maximum: float) -> float:
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise LabValidationError(f"{label}: a numeric value is required") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise LabValidationError(f"{label}: value outside [{minimum}, {maximum}]")
    return result


def _timestamp(value: str | None) -> str:
    if not isinstance(value, str) or "T" not in value:
        raise LabValidationError("measurement_utc requires an ISO timestamp with time zone")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("No time zone")
        return moment.isoformat()
    except ValueError as exc:
        raise LabValidationError("Invalid measurement_utc timestamp") from exc


def read_sweeps(csv_path: str | Path, *, max_bytes: int = DEFAULT_MAX_CSV_BYTES) -> list[BenchReading]:
    """Read bounded CSV without changing or imputing physical measurements."""
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    path = Path(csv_path)
    if path.stat().st_size > max_bytes:
        raise LabValidationError("CSV size exceeds the configured maximum")
    measurements: list[BenchReading] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        headers = reader.fieldnames
        if headers is None or len(headers) != len(set(headers)):
            raise LabValidationError("Missing or duplicate CSV headers")
        if set(headers) != set(REQUIRED_COLUMNS):
            raise LabValidationError("CSV columns must match the documented evidence contract")
        try:
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None or value.strip() == "" for value in row.values()):
                    raise LabValidationError(f"Line {line_number}: missing or extra field")
                run_id = row["run_id"]
                if len(run_id) > 100 or not all(c.isascii() and (c.isalnum() or c in "-_.") for c in run_id):
                    raise LabValidationError(f"Line {line_number}: unsafe run identifier")
                source = row["evidence_type"]
                if source not in ("synthetic", "measured"):
                    raise LabValidationError(f"Line {line_number}: evidence_type must be synthetic or measured")
                hot = _finite_float(row["hot_c"], "hot_c", -50, 200)
                cold = _finite_float(row["cold_c"], "cold_c", -50, 200)
                if hot <= cold:
                    raise LabValidationError(f"Line {line_number}: hot_c must be higher than cold_c")
                measurements.append(
                    BenchReading(
                        run_id=run_id,
                        measurement_utc=_timestamp(row["measurement_utc"]),
                        hot_c=hot,
                        cold_c=cold,
                        voltage_mv=_finite_float(row["voltage_mv"], "voltage_mv", 0, 5000),
                        current_ma=_finite_float(row["current_ma"], "current_ma", 0, 5000),
                        evidence_type=source,
                    )
                )
                if len(measurements) > 50000:
                    raise LabValidationError("CSV contains more than 50000 measurements")
        except csv.Error as exc:
            raise LabValidationError("Malformed CSV format") from exc
    if not measurements:
        raise LabValidationError("At least one bench run is required")
    return measurements


def analyze_sweeps(readings: list[BenchReading]) -> LabReport:
    """Find best **observed** P=UI per run without predicting the MPP between points."""
    if not readings:
        raise LabValidationError("At least one bench reading is required")
    evidence = {r.evidence_type for r in readings}
    if len(evidence) != 1 or not evidence.issubset({"synthetic", "measured"}):
        raise LabValidationError("Do not combine synthetic and measured observations")
    groups: dict[str, list[BenchReading]] = {}
    for reading in readings:
        groups.setdefault(reading.run_id, []).append(reading)
    summaries: list[SweepResult] = []
    for run_id, group in sorted(groups.items()):
        if len(group) < 3:
            raise LabValidationError(f"Run {run_id} needs at least three load points")
        highest = max(group, key=lambda item: item.power_w)
        gradients = [item.delta_t_k for item in group]
        span = max(gradients) - min(gradients)
        summaries.append(
            SweepResult(
                run_id=run_id,
                point_count=len(group),
                median_delta_t_k=median(gradients),
                delta_t_span_k=span,
                observed_peak_power_w=highest.power_w,
                voltage_at_peak_mv=highest.voltage_mv,
                current_at_peak_ma=highest.current_ma,
                thermal_drift_warning=span > 1.0,
            )
        )
    return LabReport(
        evidence_type=next(iter(evidence)),
        run_count=len(summaries),
        median_observed_peak_power_w=median(s.observed_peak_power_w for s in summaries),
        runs=tuple(summaries),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a measured or explicitly synthetic TEG sweep")
    parser.add_argument("--file", required=True, help="CSV following docs/METROLOGIA_TEG.md")
    args = parser.parse_args(argv)
    try:
        result = analyze_sweeps(read_sweeps(args.file))
    except (OSError, ValueError, LabValidationError) as exc:
        print(f"Thermo-IoT bench analysis: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
