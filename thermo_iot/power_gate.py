"""Engineering HOLD gate for the public, non-novel LTC3108 reference circuit.

The current open PCB puts 470uF on the 3.3V VOUT rail and exposes a separate
5V VSTORE connection. VSTORE is NOT a valid direct STM32WLE VDD supply.

The calculation assumes no active source current replenishment during the RF
event and an ideal lumped capacitance with an ESR instantaneous voltage drop.
It is NOT regulator simulation, a power-path BOM approval, or a physical test.
"""

from dataclasses import dataclass
import json
import math
from .energy import EnergyScenario, evaluate
from .radio_budget import RadioBurst, estimate_burst


STM32WL_MAX_VDD_V = 3.6
NOMINAL_LTC3108_VOUT_CURRENT_A = 0.0045


@dataclass(frozen=True)
class SupplyCandidate:
    rail: str
    vout_v: float
    minimum_v: float
    capacitance_f: float
    esr_ohm: float

    def validate(self) -> None:
        if self.rail not in ("VOUT", "VSTORE", "VLDO"):
            raise ValueError("Unknown PMIC supply rail")
        for name in ("vout_v", "minimum_v", "capacitance_f", "esr_ohm"):
            item = getattr(self, name)
            if isinstance(item, bool) or not isinstance(item, (float,int)) or not math.isfinite(item):
                raise ValueError(f"Invalid supply candidate {name}")
        if not 0 < self.vout_v <= 10 or not 0 < self.minimum_v < self.vout_v:
            raise ValueError("Invalid supply voltage or minimum")
        if not 0 < self.capacitance_f <= 10000:
            raise ValueError("Invalid supply capacitance")
        if not 0 <= self.esr_ohm <= 1000:
            raise ValueError("Invalid supply ESR")


def candidate_supply(*, rail: str = "VOUT", vout_v: float = 3.3,
                     minimum_v: float = 2.0, capacitance_f: float = 0.00047,
                     esr_ohm: float = 0.5) -> SupplyCandidate:
    """Hardware schematic A0 public reference: C6=470uF on VOUT, not 2.5F."""
    return SupplyCandidate(rail, vout_v, minimum_v, capacitance_f, esr_ohm)


def screen_reference_power(
    supply: SupplyCandidate,
    *,
    scenario: EnergyScenario | None = None,
    burst: RadioBurst | None = None,
) -> dict:
    """Conservative, non-certifying screen with explicit mismatched-rail gate.

    A green mathematical candidate ALWAYS requires independent engineering
    review; no output may authorize fabrication or deployment.
    """
    supply.validate()
    scenario = scenario or EnergyScenario(
        capacitance_f=supply.capacitance_f,
        voltage_high_v=supply.vout_v, voltage_low_v=supply.minimum_v,
    )
    burst = burst or RadioBurst(
        capacitance_f=supply.capacitance_f, cap_esr_ohm=supply.esr_ohm,
        initial_voltage_v=supply.vout_v, min_voltage_v=supply.minimum_v,
    )
    scenario.validate()
    burst.validate()

    reasons: list[str] = []
    if supply.rail == "VSTORE" or supply.vout_v > STM32WL_MAX_VDD_V:
        reasons.append("MCU overvoltage")
    if (not math.isclose(scenario.capacitance_f,supply.capacitance_f,rel_tol=1e-9)
        or not math.isclose(burst.capacitance_f,supply.capacitance_f,rel_tol=1e-9)):
        reasons.append("Capacitance mismatch")
    if (not math.isclose(scenario.voltage_high_v,supply.vout_v,rel_tol=1e-9)
        or not math.isclose(scenario.voltage_low_v,supply.minimum_v,rel_tol=1e-9)
        or not math.isclose(burst.initial_voltage_v,supply.vout_v,rel_tol=1e-9)
        or not math.isclose(burst.min_voltage_v,supply.minimum_v,rel_tol=1e-9)
        or not math.isclose(burst.cap_esr_ohm,supply.esr_ohm,rel_tol=1e-9,abs_tol=1e-12)):
        reasons.append("Voltage or ESR assumption mismatch")

    event = estimate_burst(burst)
    average = evaluate(scenario)
    if scenario.cycle_energy_j < event.total_energy_j - 1e-12:
        reasons.append("Cycle energy below radio event demand")
    if not event.above_minimum_voltage:
        reasons.append("RF burst reservoir brownout")
    if not average.sustainable:
        reasons.append("Average power or reservoir energy insufficient")

    headroom=supply.vout_v-supply.minimum_v-max(burst.tx_current_a,burst.rx_current_a)*supply.esr_ohm
    # P = V*I instantaneous + Q/C: this is a lower bound ignoring regulator
    # inefficiencies, temperature derating, DCR and measurement uncertainty.
    charge=(burst.tx_current_a*burst.tx_duration_s
            +burst.rx_current_a*burst.rx_duration_s
            +burst.extra_energy_j/supply.vout_v)
    cap_needed=charge/headroom if headroom>0 else None

    return {
        "candidate":"Public LTC3108 GN16 laboratory breakout",
        "source_rail":supply.rail,
        "installed_reference_vout_capacitance_f":supply.capacitance_f,
        "rail_voltage_v":supply.vout_v,
        "cap_esr_assumption_ohm":supply.esr_ohm,
        "tx_peak_a":burst.tx_current_a,
        "ltc3108_typical_vout_current_a":NOMINAL_LTC3108_VOUT_CURRENT_A,
        "tx_peak_exceeds_pmic_typical_output_current":
            burst.tx_current_a > NOMINAL_LTC3108_VOUT_CURRENT_A,
        "model_radio_event_j":event.total_energy_j,
        "assumed_cycle_energy_j":scenario.cycle_energy_j,
        "model_min_supply_voltage_v":event.estimated_min_voltage_v,
        "minimum_v_required":supply.minimum_v,
        "burst_voltage_screen_passed":event.above_minimum_voltage,
        "min_ideal_capacitance_f":cap_needed,
        "average_energy_model_sustainable":average.sustainable,
        "decision":"HOLD" if reasons else "ENGINEERING_REVIEW_REQUIRED",
        "blocking_reasons":reasons,
        "hardware_validated":False,
        "deployment_authorized":False,
        "fabrication_authorized":False,
        "note":(
            "Capacitor-only screening using hypothetical ESR and radio currents. "
            "The VSTORE supercapacitor cannot be counted as VOUT hold-up without "
            "a measured, regulator-qualified power path. Measured startup, "
            "brownout, output current/ESR, sensor and TTN tests remain mandatory."
        ),
    }


def main() -> int:
    print(json.dumps(screen_reference_power(candidate_supply()),indent=2,allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
