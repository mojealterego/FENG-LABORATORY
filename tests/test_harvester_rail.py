"""TEG/LTC3108 laboratory VOUT rail screening, never a fabricated board test."""
import unittest
from thermo_iot.harvester_rail import (
    RailAssumptions, evaluate_hold_up, recommended_capacitance_f,
    validate_mcu_supply,
)


class HarvesterRailTests(unittest.TestCase):
    def test_470uf_with_200ms_87ma_rf_burst_is_no_go_even_with_optimistic_pmic(self):
        c=RailAssumptions(output_capacitance_f=470e-6, pmic_current_a=0.0045,
                          cap_esr_ohm=0.15)
        result=evaluate_hold_up(c)
        self.assertEqual(result["status"],"NO_GO")
        self.assertFalse(result["estimated_voltage_qualified"])
        self.assertGreater(result["required_capacitance_f"],0.013)
        self.assertLess(result["required_capacitance_f"],0.015)
        self.assertTrue(result["optimistic_pmic_current"])
        self.assertFalse(result["physical_validation_performed"])
        self.assertIn("brownout",result["warning"].lower())

    def test_47mf_passes_only_model_not_hardware(self):
        model=RailAssumptions(output_capacitance_f=0.047,pmic_current_a=0.0045)
        result=evaluate_hold_up(model)
        self.assertEqual(result["status"],"MODEL_ONLY_PASS")
        self.assertTrue(result["estimated_voltage_qualified"])
        self.assertFalse(result["physical_validation_performed"])

    def test_vstore_max_5v25_is_not_stm32_supply(self):
        self.assertEqual(validate_mcu_supply(5.25)["status"],"NO_GO")
        self.assertEqual(validate_mcu_supply(3.3)["status"],"MODEL_ONLY_PASS")
        with self.assertRaises(ValueError):
            validate_mcu_supply(float("nan"))

    def test_pmic_assumption_above_nominal_is_not_implicitly_allowed(self):
        with self.assertRaises(ValueError):
            RailAssumptions(pmic_current_a=0.1).validate()

    def test_sensible_esr_and_charge_limit(self):
        required=recommended_capacitance_f(
            RailAssumptions(output_capacitance_f=0.00047,pmic_current_a=0.0,
                            cap_esr_ohm=0.0)
        )
        self.assertGreater(required,0.017)
        with self.assertRaises(ValueError):
            recommended_capacitance_f(
                RailAssumptions(cap_esr_ohm=20)
            )

    def test_nonfinite_or_negative_physical_inputs_fail_closed(self):
        for kwargs in (
            {"output_capacitance_f":float("inf")},
            {"tx_current_a":-1},
            {"min_voltage_v":3.4},
            {"tx_duration_s":float("nan")},
            {"pmic_current_a":-0.1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    RailAssumptions(**kwargs).validate()


if __name__=="__main__":
    unittest.main()
