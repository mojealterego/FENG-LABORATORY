"""Conservative average-power analysis for a batteryless sensing node.

No thermoelectric material performance is inferred from a pipe-to-air gradient.
Pass measured electrical TEG power as input. Burst current, ESR, converter
cold-start, charge leakage, radio MAC retries and sensor warm-up require
separate laboratory validation; this is a screening model only.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class EnergyScenario:
    teg_power_w: float = 0.0001
    efficiency: float = 0.65
    sleep_power_w: float = 0.000008
    cycle_energy_j: float = 0.0219
    capacitance_f: float = 2.5
    voltage_high_v: float = 3.3
    voltage_low_v: float = 2.0
    airtime_s: float = 0.2
    duty_cycle: float = 0.01

    def validate(self) -> None:
        numbers = vars(self)
        if any(not math.isfinite(x) for x in numbers.values()):
            raise ValueError("All inputs must be finite")
        if self.teg_power_w < 0 or self.sleep_power_w < 0:
            raise ValueError("Powers must be non-negative")
        if not 0 < self.efficiency <= 1 or not 0 < self.duty_cycle <= 1:
            raise ValueError("Efficiency and duty cycle must be in (0, 1]")
        if self.cycle_energy_j <= 0 or self.capacitance_f <= 0 or self.airtime_s <= 0:
            raise ValueError("Energy, capacitance and airtime must be positive")
        if not 0 <= self.voltage_low_v < self.voltage_high_v:
            raise ValueError("Voltage range must satisfy 0 <= low < high")


def stored_energy_j(capacitance_f: float, voltage_high_v: float, voltage_low_v: float) -> float:
    """Ideal usable capacitor energy, before losses or reserve derating."""
    if any(not math.isfinite(v) for v in (capacitance_f, voltage_high_v, voltage_low_v)):
        raise ValueError("Inputs must be finite")
    if capacitance_f <= 0 or not 0 <= voltage_low_v < voltage_high_v:
        raise ValueError("Invalid capacitance or voltage range")
    return 0.5 * capacitance_f * (voltage_high_v**2 - voltage_low_v**2)


@dataclass(frozen=True)
class EnergyResult:
    buffer_energy_j: float
    usable_average_power_w: float
    net_average_power_w: float
    energy_limited_interval_s: float
    duty_limited_interval_s: float
    min_interval_s: float
    max_cycles_per_day: int
    buffer_cycles_without_harvest: int
    sustainable: bool


def evaluate(scenario: EnergyScenario) -> EnergyResult:
    scenario.validate()
    available = stored_energy_j(scenario.capacitance_f, scenario.voltage_high_v, scenario.voltage_low_v)
    after_conversion = scenario.teg_power_w * scenario.efficiency
    net = after_conversion - scenario.sleep_power_w
    has_burst_reserve = available >= scenario.cycle_energy_j
    sustainable = net > 0 and has_burst_reserve
    energy_interval = scenario.cycle_energy_j / net if net > 0 else math.inf
    duty_interval = scenario.airtime_s / scenario.duty_cycle
    interval = max(energy_interval, duty_interval) if sustainable else math.inf
    per_day = math.floor(86400.0 / interval) if sustainable else 0
    return EnergyResult(
        buffer_energy_j=available,
        usable_average_power_w=after_conversion,
        net_average_power_w=net,
        energy_limited_interval_s=energy_interval,
        duty_limited_interval_s=duty_interval,
        min_interval_s=interval,
        max_cycles_per_day=per_day,
        buffer_cycles_without_harvest=math.floor(available / scenario.cycle_energy_j),
        sustainable=sustainable,
    )
