"""First-order radio burst budget: capacitor current and ESR screening.

Defaults illustrate STM32WLE5 RF TX/RX data-sheet values, not a fully measured
LoRaWAN node, PMIC/antenna path or a complete communications event.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RadioBurst:
    initial_voltage_v: float = 3.3
    min_voltage_v: float = 2.0
    tx_current_a: float = 0.087
    tx_duration_s: float = 0.2
    rx_current_a: float = 0.00482
    rx_duration_s: float = 1.0
    extra_energy_j: float = 0.005
    capacitance_f: float = 2.5
    cap_esr_ohm: float = 0.5

    def validate(self) -> None:
        for value in vars(self).values():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("All burst parameters must be finite real numbers")
        if not 0 < self.initial_voltage_v <= 10 or not 0 < self.min_voltage_v < self.initial_voltage_v:
            raise ValueError("Invalid voltage range")
        if self.tx_current_a < 0 or self.rx_current_a < 0 or self.tx_current_a > 10 or self.rx_current_a > 10:
            raise ValueError("Radio current outside supported model bounds")
        if self.tx_duration_s < 0 or self.rx_duration_s < 0 or self.tx_duration_s > 10000 or self.rx_duration_s > 10000:
            raise ValueError("Invalid radio airtime duration")
        if self.extra_energy_j < 0 or self.extra_energy_j > 1e6:
            raise ValueError("Invalid extra energy")
        if not 0 < self.capacitance_f <= 10000 or not 0 <= self.cap_esr_ohm <= 10000:
            raise ValueError("Invalid capacitor parameters")


@dataclass(frozen=True)
class RadioBurstResult:
    tx_energy_j: float
    rx_energy_j: float
    total_energy_j: float
    reservoir_discharge_v: float
    esr_drop_v: float
    worst_instantaneous_drop_v: float
    estimated_min_voltage_v: float
    above_minimum_voltage: bool
    note: str = "Rough capacitor-only estimate; no regulator dynamics, ESR spread or device validation."


def estimate_burst(config: RadioBurst) -> RadioBurstResult:
    """Conservative screening approximation; supply regulation is excluded."""
    config.validate()
    tx = config.initial_voltage_v * config.tx_current_a * config.tx_duration_s
    rx = config.initial_voltage_v * config.rx_current_a * config.rx_duration_s
    total = tx + rx + config.extra_energy_j
    charge_c = (config.tx_current_a * config.tx_duration_s
                + config.rx_current_a * config.rx_duration_s
                + config.extra_energy_j / config.initial_voltage_v)
    capacitive_drop = charge_c / config.capacitance_f
    resistive_drop = max(config.tx_current_a, config.rx_current_a) * config.cap_esr_ohm
    sag = capacitive_drop + resistive_drop
    vmin = max(0.0, config.initial_voltage_v - sag)
    return RadioBurstResult(
        tx_energy_j=tx,
        rx_energy_j=rx,
        total_energy_j=total,
        reservoir_discharge_v=capacitive_drop,
        esr_drop_v=resistive_drop,
        worst_instantaneous_drop_v=sag,
        estimated_min_voltage_v=vmin,
        above_minimum_voltage=vmin >= config.min_voltage_v,
    )
