"""Adaptive sampling feasibility planner using measured electrical power.

This is a design-time decision aid, not real-time control firmware. It does not
model peak-current droop, supercap ESR, PMIC startup or LoRaWAN join energy.
"""

from dataclasses import dataclass
import math

from .energy import EnergyScenario, evaluate


@dataclass(frozen=True)
class SchedulerPolicy:
    min_interval_s: int = 60
    max_interval_s: int = 3600
    reserve_fraction: float = 0.2
    energy_margin: float = 1.5

    def validate(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (self.min_interval_s, self.max_interval_s)
        ):
            raise ValueError("Sampling periods must be whole seconds")
        if self.min_interval_s < 1 or self.max_interval_s < self.min_interval_s:
            raise ValueError("Intervals must satisfy 1 <= min_interval_s <= max_interval_s")
        if not math.isfinite(self.reserve_fraction) or not 0 <= self.reserve_fraction < 1:
            raise ValueError("Reserve fraction must be in [0, 1)")
        if not math.isfinite(self.energy_margin) or self.energy_margin < 1:
            raise ValueError("Energy margin must be finite and >= 1")


@dataclass(frozen=True)
class ScheduleDecision:
    state: str
    interval_s: int | None
    available_buffer_j: float
    required_buffer_j: float
    net_average_power_w: float
    energy_limited_interval_s: float | None
    duty_limited_interval_s: float


def decide_interval(
    scenario: EnergyScenario,
    measured_voltage_v: float,
    policy: SchedulerPolicy = SchedulerPolicy(),
) -> ScheduleDecision:
    """Screen a periodic sensing interval against average harvesting and reserve.

    'eligible' means *only* that idealized average-power/buffer constraints
    pass. The function cannot authorize actual field transmission.
    """
    scenario.validate()
    policy.validate()
    if (
        isinstance(measured_voltage_v, bool)
        or not isinstance(measured_voltage_v, (int, float))
        or not math.isfinite(measured_voltage_v)
        or not 0 <= measured_voltage_v <= scenario.voltage_high_v
    ):
        raise ValueError("Measured buffer voltage is outside the configured voltage range")
    result = evaluate(scenario)
    available = (
        0.5 * scenario.capacitance_f *
        (measured_voltage_v ** 2 - scenario.voltage_low_v ** 2)
        if measured_voltage_v > scenario.voltage_low_v else 0.0
    )
    required = (
        policy.reserve_fraction * result.buffer_energy_j
        + policy.energy_margin * scenario.cycle_energy_j
    )
    net = result.net_average_power_w
    energy_period = (
        scenario.cycle_energy_j * policy.energy_margin / net if net > 0 else None
    )
    duty_period = scenario.airtime_s / scenario.duty_cycle

    if net <= 0:
        state, interval = "power_deficit", None
    else:
        constrained = max(
            policy.min_interval_s,
            math.ceil(energy_period - 1e-10),
            math.ceil(duty_period - 1e-10),
        )
        if constrained > policy.max_interval_s:
            state, interval = "interval_exceeds_limit", None
        elif available < required:
            state, interval = "charging", None
        else:
            state, interval = "eligible", constrained
    return ScheduleDecision(
        state=state, interval_s=interval, available_buffer_j=available,
        required_buffer_j=required, net_average_power_w=net,
        energy_limited_interval_s=energy_period,
        duty_limited_interval_s=duty_period,
    )
