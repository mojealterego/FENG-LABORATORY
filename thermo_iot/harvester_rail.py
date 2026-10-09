"""Vendor-reference LTC3108 output-capacitor hold-up screening.

Public-domain first-order Q=C*dV and series-resistance approximation only.
No private harvester hardware claim, patent-sensitive circuit or measurement.
Source: Analog Devices LTC3108 datasheet GN16 VOUT/VSTORE descriptions.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math


@dataclass(frozen=True)
class RailAssumptions:
    """Representative STM32WLE RF profile; all values are ASSUMED, not measured.

    PMIC available current defaults to zero. Using 4.5mA is an OPTIMISTIC
    typical LTC3108 VOUT delivery scenario, not a guaranteed minimum output.
    """
    initial_voltage_v: float = 3.3
    min_voltage_v: float = 2.0
    tx_current_a: float = 0.087
    tx_duration_s: float = 0.2
    rx_current_a: float = 0.00482
    rx_duration_s: float = 1.0
    extra_energy_j: float = 0.0
    output_capacitance_f: float = 470e-6
    cap_esr_ohm: float = 0.15
    pmic_current_a: float = 0.0

    def validate(self) -> None:
        for name,value in vars(self).items():
            if (isinstance(value,bool) or not isinstance(value,(int,float))
                    or not math.isfinite(value)):
                raise ValueError(f"{name} must be a finite real number")
        if not 1.8 <= self.min_voltage_v < self.initial_voltage_v <= 3.6:
            raise ValueError("Chosen STM32WLE VDD must be within 1.8..3.6V")
        for key in ("tx_current_a","rx_current_a"):
            if not 0<=getattr(self,key)<=0.5:
                raise ValueError("RF currents must be nonnegative and <=0.5 A")
        for key in ("tx_duration_s","rx_duration_s"):
            if not 0<=getattr(self,key)<=30:
                raise ValueError("Burst durations must be 0..30 seconds")
        if not 0 <= self.extra_energy_j <= 1.0:
            raise ValueError("Extra energy must be 0..1 J")
        if not 0 < self.output_capacitance_f <= 100:
            raise ValueError("Capacitance must be 0..100 F")
        if not 0 <= self.cap_esr_ohm <= 20:
            raise ValueError("ESR must be 0..20 ohms")
        if not 0 <= self.pmic_current_a <= 0.0045:
            raise ValueError("Use <=4.5 mA optimistic LTC3108 reference source current")


def _charge_and_sag(model: RailAssumptions) -> tuple[float,float]:
    tx=max(0.0,model.tx_current_a-model.pmic_current_a)
    rx=max(0.0,model.rx_current_a-model.pmic_current_a)
    total_charge=(tx*model.tx_duration_s+rx*model.rx_duration_s
                  +model.extra_energy_j/model.initial_voltage_v)
    resistive_drop=max(tx,rx)*model.cap_esr_ohm
    return total_charge,resistive_drop


def recommended_capacitance_f(model: RailAssumptions) -> float:
    """Minimum first-order ideal capacitance incl. instantaneous ESR loss.

    This is a preflight screening lower bound, NOT a guaranteed design value.
    Capacitor tolerance/temperature/aging, regulator control, switch losses,
    startup, LoRaWAN retries, overshoot and manufacturer margins are excluded.
    """
    model.validate()
    total_charge,resistive_drop=_charge_and_sag(model)
    available=model.initial_voltage_v-model.min_voltage_v-resistive_drop
    if available<=0:
        raise ValueError("ESR instantaneous droop exhausts the voltage budget")
    return total_charge/available


def evaluate_hold_up(model: RailAssumptions) -> dict:
    model.validate()
    q,esr_drop=_charge_and_sag(model)
    try:
        minimum_cap=recommended_capacitance_f(model)
    except ValueError:
        minimum_cap=None
    estimated_v=max(0.0,model.initial_voltage_v-q/model.output_capacitance_f-esr_drop)
    qualified=estimated_v>=model.min_voltage_v and minimum_cap is not None
    return {
        "status":"MODEL_ONLY_PASS" if qualified else "NO_GO",
        "rail":"LTC3108 VOUT nominal 3.3V; NOT VSTORE ~5.25V",
        "candidate_capacitance_f":model.output_capacitance_f,
        "assumed_initial_voltage_v":model.initial_voltage_v,
        "required_capacitance_f":minimum_cap,
        "estimated_voltage_after_burst_v":estimated_v,
        "min_operating_voltage_v":model.min_voltage_v,
        "reference_net_charge_c":q,
        "esr_step_drop_v":esr_drop,
        "assumed_pmic_supply_a":model.pmic_current_a,
        "optimistic_pmic_current":model.pmic_current_a>0,
        "estimated_voltage_qualified":qualified,
        "physical_validation_performed":False,
        "fabrication_authorized":False,
        "warning":(
            "First-order electrical brownout screening only. Assumed 4.5mA is a "
            "typical, not guaranteed LTC3108 capability. Actual TX/RX profile, "
            "capacitance tolerance, ESR, VOUT/VSTORE interaction, recharge time, "
            "regulator dynamics, PMIC startup and RF transmission MUST be measured."
        ),
    }


def validate_mcu_supply(voltage_v:float, *, min_v:float=1.8, max_v:float=3.6) -> dict:
    for name,value in (("voltage_v",voltage_v),("min_v",min_v),("max_v",max_v)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite real number")
    if not 0<min_v<max_v<10 or voltage_v<0:
        raise ValueError("Invalid voltage or allowed MCU supply range")
    safe=min_v<=voltage_v<=max_v
    return {
        "status":"MODEL_ONLY_PASS" if safe else "NO_GO",
        "voltage_v":voltage_v,
        "expected_range_v":[min_v,max_v],
        "not_hardware_validated":True,
        "warning":"Nominal voltage check only; transients, absolute maximum and actual VDD must be measured.",
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Lab-only output capacitor / LoRaWAN current rail preflight")
    p.add_argument("--capacitance-uf",type=float,default=470)
    p.add_argument("--esr-ohm",type=float,default=0.15)
    p.add_argument("--pmic-current-ma",type=float,default=0)
    args=p.parse_args(argv)
    try:
        cfg=RailAssumptions(output_capacitance_f=args.capacitance_uf*1e-6,
                            cap_esr_ohm=args.esr_ohm,
                            pmic_current_a=args.pmic_current_ma/1000)
        report=evaluate_hold_up(cfg)
    except (ValueError,OverflowError) as exc:
        p.error(str(exc))
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["status"]=="MODEL_ONLY_PASS" else 3


if __name__=="__main__":
    raise SystemExit(main())
