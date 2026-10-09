"""Conservative capacitor-energy trace simulation using electrical TEG power.

A TEG power sample is held until the next timestamp. A periodic sensing event
uses stored capacitor energy only if the margin+reserve gate is met.
No ESR, cold-start, current sag or actual network MAC is simulated.
"""

import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sys

from .energy import EnergyScenario, stored_energy_j

MAX_TRACE_BYTES = 5_000_000
MAX_EVENTS = 2_000_000
MAX_DURATION_S = 366 * 86400


@dataclass(frozen=True)
class PowerPoint:
    elapsed_s: int
    teg_power_w: float


@dataclass(frozen=True)
class PowerTrace:
    evidence_type: str
    points: tuple[PowerPoint, ...]


@dataclass(frozen=True)
class TraceResult:
    evidence_type: str
    duration_s: int
    requested_period_s: int
    planned_opportunities: int
    successful_cycles: int
    deferred_cycles: int
    delivery_fraction: float | None
    initial_buffer_energy_j: float
    final_buffer_energy_j: float
    minimum_buffer_energy_j: float
    harvested_energy_j: float
    standby_demand_energy_j: float
    spilled_energy_j: float
    depleted_seconds: float
    interpretation: str = "Screening simulation only; not laboratory or field evidence."

    def to_dict(self) -> dict:
        return asdict(self)


def _finite_real(value: object, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number")
    number = float(value)
    if not math.isfinite(number) or number < minimum or number > maximum:
        raise ValueError(f"{name} must be finite and within [{minimum}, {maximum}]")
    return number


def validate_trace(trace: PowerTrace) -> None:
    if trace.evidence_type not in {"synthetic", "measured"}:
        raise ValueError("Evidence provenance must be synthetic or measured")
    if len(trace.points) < 2 or len(trace.points) > 50000:
        raise ValueError("A trace must contain between two and 50000 time points")
    previous = -1
    for point in trace.points:
        if not isinstance(point.elapsed_s, int) or isinstance(point.elapsed_s, bool):
            raise ValueError("Trace time must be a whole number of seconds")
        if not previous < point.elapsed_s <= MAX_DURATION_S:
            raise ValueError("Trace times must increase strictly and be within one year")
        _finite_real(point.teg_power_w, "teg_power_w", 0, 1000)
        previous = point.elapsed_s
    if trace.points[0].elapsed_s != 0:
        raise ValueError("Trace must begin at elapsed_s = 0")


def load_power_trace(path: str | Path) -> PowerTrace:
    """Read a bounded CSV; never silently mix simulated and observed data."""
    file = Path(path)
    if file.stat().st_size > MAX_TRACE_BYTES:
        raise ValueError("Power trace exceeds size limit")
    points: list[PowerPoint] = []
    provenance: set[str] = set()
    with file.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames is None or reader.fieldnames != [
            "elapsed_s", "teg_power_uw", "evidence_type"
        ]:
            raise ValueError("Power trace needs exact elapsed_s,teg_power_uw,evidence_type headers")
        try:
            for row in reader:
                if None in row or any(v is None or v.strip() == "" for v in row.values()):
                    raise ValueError("Missing or extra CSV field")
                try:
                    stamp = int(row["elapsed_s"])
                    power = float(row["teg_power_uw"]) * 1e-6
                except ValueError as exc:
                    raise ValueError("Invalid power trace numeric field") from exc
                points.append(PowerPoint(stamp, power))
                provenance.add(row["evidence_type"])
                if len(points) > 50000:
                    raise ValueError("Too many power trace points")
        except csv.Error as exc:
            raise ValueError("Invalid CSV") from exc
    if len(provenance) != 1:
        raise ValueError("Mixed or missing provenance values")
    trace = PowerTrace(next(iter(provenance)), tuple(points))
    validate_trace(trace)
    return trace


def simulate_trace(
    trace: PowerTrace,
    scenario: EnergyScenario,
    *,
    period_s: int,
    initial_voltage_v: float,
    reserve_fraction: float = 0.1,
    cycle_energy_margin: float = 1.2,
) -> TraceResult:
    """Integrate sample-and-hold TEG power and periodic cycle opportunities.

    Fixed TX spacing is only an abstract duty constraint, not regulatory or
    LoRaWAN stack compliance. 'Successful' means ENERGETICALLY ACCEPTED.
    """
    scenario.validate()
    validate_trace(trace)
    voltage = _finite_real(initial_voltage_v, "initial_voltage_v", 0, scenario.voltage_high_v)
    reserve = _finite_real(reserve_fraction, "reserve_fraction", 0, 0.999999)
    margin = _finite_real(cycle_energy_margin, "cycle_energy_margin", 1, 100)
    if not isinstance(period_s, int) or isinstance(period_s, bool) or period_s < 1:
        raise ValueError("period_s must be a positive integer")
    if period_s + 1e-9 < scenario.airtime_s / scenario.duty_cycle:
        raise ValueError("Requested period violates the configured radio duty interval")
    last_time = trace.points[-1].elapsed_s
    if last_time // period_s > MAX_EVENTS:
        raise ValueError("Simulation requires more than two million transmit decisions")
    cap_max = stored_energy_j(scenario.capacitance_f, scenario.voltage_high_v, scenario.voltage_low_v)
    available = (
        stored_energy_j(scenario.capacitance_f, voltage, scenario.voltage_low_v)
        if voltage > scenario.voltage_low_v else 0.0
    )
    initial = available
    minimum = available
    harvested = 0.0
    standby_demand = 0.0
    spilled = 0.0
    depleted = 0.0
    successes = 0
    deferred = 0
    opportunities = 0
    current_time = 0
    next_cycle = period_s
    next_change = 1
    points = trace.points
    while current_time < last_time:
        transition = points[next_change].elapsed_s
        instant = min(transition, next_cycle, last_time)
        dt = instant - current_time
        gross = points[next_change - 1].teg_power_w * scenario.efficiency * dt
        idle = scenario.sleep_power_w * dt
        harvested += gross
        standby_demand += idle
        change = gross - idle
        if change < 0 and available + change < 0:
            depleted += dt - (available / (-change / dt))
        if available == 0 and change == 0:
            depleted += dt
        unconstrained = available + change
        spilled += max(0.0, unconstrained - cap_max)
        available = min(cap_max, max(0.0, unconstrained))
        minimum = min(minimum, available)
        current_time = instant
        if current_time == next_cycle:
            opportunities += 1
            required = cap_max * reserve + scenario.cycle_energy_j * margin
            if available + 1e-12 >= required:
                available = max(0.0, available - scenario.cycle_energy_j)
                successes += 1
                minimum = min(minimum, available)
            else:
                deferred += 1
            next_cycle += period_s
        if current_time == transition and next_change < len(points) - 1:
            next_change += 1
    return TraceResult(
        evidence_type=trace.evidence_type,
        duration_s=last_time,
        requested_period_s=period_s,
        planned_opportunities=opportunities,
        successful_cycles=successes,
        deferred_cycles=deferred,
        delivery_fraction=successes / opportunities if opportunities else None,
        initial_buffer_energy_j=initial,
        final_buffer_energy_j=available,
        minimum_buffer_energy_j=minimum,
        harvested_energy_j=harvested,
        standby_demand_energy_j=standby_demand,
        spilled_energy_j=spilled,
        depleted_seconds=max(0.0, depleted),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Energy feasibility under time-varying TEG electrical power"
    )
    parser.add_argument("--file", required=True)
    parser.add_argument("--period-s", type=int, default=600)
    parser.add_argument("--initial-voltage-v", type=float, default=2.8)
    parser.add_argument("--efficiency", type=float, default=0.65)
    parser.add_argument("--sleep-uw", type=float, default=8.0)
    parser.add_argument("--cycle-mj", type=float, default=21.9)
    parser.add_argument("--reserve-fraction", type=float, default=0.1)
    parser.add_argument("--energy-margin", type=float, default=1.2)
    args = parser.parse_args(argv)
    try:
        result = simulate_trace(
            load_power_trace(args.file),
            EnergyScenario(
                teg_power_w=0,
                efficiency=args.efficiency,
                sleep_power_w=args.sleep_uw * 1e-6,
                cycle_energy_j=args.cycle_mj * 1e-3,
            ),
            period_s=args.period_s,
            initial_voltage_v=args.initial_voltage_v,
            reserve_fraction=args.reserve_fraction,
            cycle_energy_margin=args.energy_margin,
        )
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Invalid energy trace: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
