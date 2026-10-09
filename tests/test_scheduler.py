"""Adaptive duty-cycle screening contract (not on-device power control)."""

import math
import unittest

from thermo_iot.energy import EnergyScenario
from thermo_iot.scheduler import SchedulerPolicy, decide_interval


class SchedulerTests(unittest.TestCase):
    def test_nominal_case_obeys_configured_minimum(self):
        scenario = EnergyScenario(teg_power_w=0.001, efficiency=1, sleep_power_w=0,
                                  cycle_energy_j=0.02, airtime_s=0.2)
        result = decide_interval(scenario, measured_voltage_v=3.3)
        self.assertEqual(result.state, "eligible")
        self.assertEqual(result.interval_s, 60)

    def test_insufficient_buffer_defers_transmission(self):
        scenario = EnergyScenario(teg_power_w=0.001, efficiency=1, sleep_power_w=0)
        result = decide_interval(scenario, measured_voltage_v=2.1)
        self.assertEqual(result.state, "charging")
        self.assertIsNone(result.interval_s)

    def test_voltage_below_converter_floor_defers_transmission(self):
        result = decide_interval(EnergyScenario(), measured_voltage_v=1.5)
        self.assertEqual(result.state, "charging")

    def test_negative_net_power_blocks_periodic_operation(self):
        scenario = EnergyScenario(teg_power_w=0, sleep_power_w=0.001)
        result = decide_interval(scenario, measured_voltage_v=3.3)
        self.assertEqual(result.state, "power_deficit")
        self.assertIsNone(result.interval_s)

    def test_duty_cycle_constraint_dominates(self):
        scenario = EnergyScenario(teg_power_w=0.1, sleep_power_w=0,
                                  efficiency=1, airtime_s=3, duty_cycle=0.01)
        result = decide_interval(scenario, measured_voltage_v=3.3)
        self.assertEqual(result.state, "eligible")
        self.assertEqual(result.interval_s, 300)

    def test_energy_budget_constraint_dominates(self):
        scenario = EnergyScenario(teg_power_w=0.001, efficiency=0.5,
                                  sleep_power_w=0.0001, cycle_energy_j=0.02,
                                  airtime_s=0.2)
        result = decide_interval(scenario, measured_voltage_v=3.3)
        self.assertEqual(result.state, "eligible")
        self.assertEqual(result.interval_s, 75)

    def test_period_exceeding_policy_cap_is_infeasible(self):
        scenario = EnergyScenario(teg_power_w=0.00001, efficiency=1,
                                  sleep_power_w=0.000008)
        result = decide_interval(scenario, measured_voltage_v=3.3)
        self.assertEqual(result.state, "interval_exceeds_limit")
        self.assertIsNone(result.interval_s)

    def test_policy_validation_rejects_bad_reserve_and_interval(self):
        for policy in (SchedulerPolicy(reserve_fraction=1),
                       SchedulerPolicy(reserve_fraction=-0.01),
                       SchedulerPolicy(min_interval_s=5000, max_interval_s=3600)):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                decide_interval(EnergyScenario(), 3.0, policy)

    def test_invalid_measured_voltage_is_rejected(self):
        for value in (-1.0, math.nan, math.inf, 6.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decide_interval(EnergyScenario(), value)


if __name__ == "__main__":
    unittest.main()
