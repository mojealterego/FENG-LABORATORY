import math
import unittest

from thermo_iot.energy import EnergyScenario, evaluate, stored_energy_j


class EnergyBudgetTests(unittest.TestCase):
    def test_supercapacitor_usable_energy(self):
        self.assertAlmostEqual(stored_energy_j(2.5, 3.3, 2.0), 8.6125)

    def test_rejects_reversed_voltage_range(self):
        with self.assertRaises(ValueError):
            stored_energy_j(2.5, 2.0, 3.3)

    def test_rejects_negative_power(self):
        with self.assertRaises(ValueError):
            EnergyScenario(teg_power_w=-0.01).validate()

    def test_zero_net_power_is_unsustainable(self):
        result = evaluate(EnergyScenario(teg_power_w=0.000008, efficiency=1.0, sleep_power_w=0.000008))
        self.assertFalse(result.sustainable)
        self.assertTrue(math.isinf(result.min_interval_s))
        self.assertEqual(result.max_cycles_per_day, 0)

    def test_interval_follows_net_power(self):
        s = EnergyScenario(teg_power_w=0.001, efficiency=0.5, sleep_power_w=0.0001, cycle_energy_j=0.02, airtime_s=0.01)
        result = evaluate(s)
        self.assertAlmostEqual(result.min_interval_s, 50.0)
        self.assertTrue(result.sustainable)

    def test_duty_cycle_binds_even_when_energy_is_plentiful(self):
        s = EnergyScenario(teg_power_w=0.1, efficiency=1.0, sleep_power_w=0, cycle_energy_j=0.01, airtime_s=1.0, duty_cycle=0.01)
        result = evaluate(s)
        self.assertAlmostEqual(result.min_interval_s, 100.0)

    def test_buffer_too_small_for_burst_is_not_viable(self):
        s = EnergyScenario(capacitance_f=0.001, voltage_high_v=3.3, voltage_low_v=2.0, cycle_energy_j=0.0219)
        result = evaluate(s)
        self.assertFalse(result.sustainable)
        self.assertEqual(result.max_cycles_per_day, 0)

    def test_reference_126_mw_per_m2_is_not_fast_for_tiny_area(self):
        s = EnergyScenario(teg_power_w=0.00126 * 0.01, efficiency=0.65, sleep_power_w=8e-6, cycle_energy_j=0.0219, airtime_s=0.2)
        r = evaluate(s)
        self.assertGreater(r.min_interval_s, 86400)

    def test_invalid_efficiency_and_duty(self):
        for scenario in (EnergyScenario(efficiency=1.2), EnergyScenario(duty_cycle=0), EnergyScenario(airtime_s=0)):
            with self.subTest(scenario=scenario):
                with self.assertRaises(ValueError):
                    scenario.validate()

    def test_cycles_without_harvest_truncate(self):
        s = EnergyScenario(teg_power_w=0, sleep_power_w=0, cycle_energy_j=2.0)
        r = evaluate(s)
        self.assertEqual(r.buffer_cycles_without_harvest, 4)


if __name__ == '__main__':
    unittest.main()
