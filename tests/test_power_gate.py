"""A datasheet candidate capacitor must not be confused with a physical RF supply.

No test in this file is evidence of a real STM32 or PMIC power measurement.
"""
import unittest

from thermo_iot.energy import EnergyScenario
from thermo_iot.radio_budget import RadioBurst
from thermo_iot.power_gate import screen_reference_power, candidate_supply


class PowerGateTests(unittest.TestCase):
    def test_populated_470uf_vout_cannot_run_87ma_rf_burst(self):
        result=screen_reference_power(candidate_supply())
        self.assertEqual(result["decision"],"HOLD")
        self.assertEqual(result["source_rail"],"VOUT")
        self.assertFalse(result["burst_voltage_screen_passed"])
        self.assertGreater(result["min_ideal_capacitance_f"],0.00047)
        self.assertFalse(result["hardware_validated"])
        self.assertFalse(result["deployment_authorized"])

    def test_vstore_direct_mcu_power_is_never_approved(self):
        result=screen_reference_power(candidate_supply(rail="VSTORE",vout_v=5.25))
        self.assertEqual(result["decision"],"HOLD")
        self.assertIn("MCU overvoltage",result["blocking_reasons"])

    def test_risky_219mj_cycle_assumption_rejected_even_with_big_cap(self):
        burst=RadioBurst(capacitance_f=2.5,cap_esr_ohm=0.1)
        scenario=EnergyScenario(capacitance_f=2.5,cycle_energy_j=0.0219)
        result=screen_reference_power(candidate_supply(capacitance_f=2.5,esr_ohm=0.1),
                                      scenario=scenario,burst=burst)
        self.assertIn("Cycle energy below radio event demand",result["blocking_reasons"])
        self.assertEqual(result["decision"],"HOLD")

    def test_adequate_theoretical_rail_is_engineering_review_not_field_ready(self):
        burst=RadioBurst(capacitance_f=2.5,cap_esr_ohm=0.1)
        scenario=EnergyScenario(capacitance_f=2.5,cycle_energy_j=0.2)
        result=screen_reference_power(candidate_supply(capacitance_f=2.5,esr_ohm=0.1),
                                      scenario=scenario,burst=burst)
        self.assertEqual(result["decision"],"ENGINEERING_REVIEW_REQUIRED")
        self.assertFalse(result["hardware_validated"])
        self.assertFalse(result["deployment_authorized"])

    def test_different_capacitance_assumptions_are_a_hard_block(self):
        result=screen_reference_power(candidate_supply(capacitance_f=0.00047),
                                      scenario=EnergyScenario(capacitance_f=2.5))
        self.assertIn("Capacitance mismatch",result["blocking_reasons"])

    def test_negative_voltages_and_unreal_supply_fail_closed(self):
        for supply in (
            candidate_supply(vout_v=0),
            candidate_supply(capacitance_f=0),
            candidate_supply(esr_ohm=-0.1),
        ):
            with self.subTest(supply=supply),self.assertRaises(ValueError):
                screen_reference_power(supply)


if __name__=="__main__":
    unittest.main()
