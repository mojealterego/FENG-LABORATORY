"""Regression tests for time-varying electrical input and capacitor reserve."""
import math
import tempfile
import unittest
from pathlib import Path
from thermo_iot.energy import EnergyScenario
from thermo_iot.trace import PowerPoint, PowerTrace, load_power_trace, simulate_trace


class PowerTraceTests(unittest.TestCase):
    def setUp(self):
        self.scenario = EnergyScenario(
            teg_power_w=0.0, efficiency=1.0, sleep_power_w=0.0,
            cycle_energy_j=0.25, capacitance_f=1.0,
            voltage_low_v=2.0, voltage_high_v=3.0,
            airtime_s=0.2, duty_cycle=0.01,
        )

    def test_one_interval_harvest_and_transmit_preserves_energy(self):
        trace = PowerTrace("synthetic", (PowerPoint(0, 0.01), PowerPoint(60, 0.01)))
        r = simulate_trace(trace, self.scenario, period_s=60, initial_voltage_v=2.0)
        self.assertEqual(r.successful_cycles, 1)
        self.assertEqual(r.deferred_cycles, 0)
        self.assertAlmostEqual(r.final_buffer_energy_j, 0.35, places=8)
        self.assertAlmostEqual(r.harvested_energy_j, 0.6)
        self.assertEqual(r.evidence_type, "synthetic")

    def test_no_harvest_standby_depletes_without_negative_energy(self):
        scenario = EnergyScenario(
            teg_power_w=0, efficiency=1, sleep_power_w=0.01,
            cycle_energy_j=0.25, capacitance_f=1.0,
            voltage_low_v=2.0, voltage_high_v=3.0,
            airtime_s=0.2, duty_cycle=0.01,
        )
        trace = PowerTrace("synthetic", (PowerPoint(0, 0), PowerPoint(600, 0)))
        r = simulate_trace(trace, scenario, period_s=60, initial_voltage_v=2.5)
        self.assertEqual(r.successful_cycles, 0)
        self.assertEqual(r.deferred_cycles, 10)
        self.assertEqual(r.final_buffer_energy_j, 0)
        self.assertGreater(r.depleted_seconds, 0)

    def test_duty_interval_blocks_illegal_scenario(self):
        trace = PowerTrace("synthetic", (PowerPoint(0, 0.1), PowerPoint(60, 0.1)))
        with self.assertRaises(ValueError):
            simulate_trace(trace, self.scenario, period_s=10, initial_voltage_v=3)

    def test_non_monotonic_or_negative_power_rejected(self):
        for points in ((PowerPoint(0, 1), PowerPoint(0, 1)),
                       (PowerPoint(0, 1), PowerPoint(1, -1)),
                       (PowerPoint(1, 1), PowerPoint(2, 1))):
            with self.subTest(points=points), self.assertRaises(ValueError):
                simulate_trace(PowerTrace("synthetic", points), self.scenario,
                               period_s=60, initial_voltage_v=3)

    def test_step_change_in_input_power(self):
        trace = PowerTrace("synthetic", (
            PowerPoint(0, 0.01), PowerPoint(60, 0), PowerPoint(120, 0)))
        r = simulate_trace(trace, self.scenario, period_s=60, initial_voltage_v=2.0)
        self.assertEqual(r.successful_cycles, 1)
        self.assertEqual(r.deferred_cycles, 1)
        self.assertAlmostEqual(r.final_buffer_energy_j, 0.35)

    def test_upper_energy_is_clamped_and_excess_recorded(self):
        trace = PowerTrace("synthetic", (PowerPoint(0, 1), PowerPoint(60, 1)))
        r = simulate_trace(trace, self.scenario, period_s=60, initial_voltage_v=3.0)
        self.assertEqual(r.successful_cycles, 1)
        self.assertAlmostEqual(r.final_buffer_energy_j, 2.25)
        self.assertAlmostEqual(r.spilled_energy_j, 60.0)

    def test_invalid_trace_or_initial_voltage_rejected(self):
        trace = PowerTrace("synthetic", (PowerPoint(0, 0), PowerPoint(60, 0)))
        for voltage in (-1.0, math.nan, 3.01):
            with self.subTest(voltage=voltage), self.assertRaises(ValueError):
                simulate_trace(trace, self.scenario, period_s=60, initial_voltage_v=voltage)
        with self.assertRaises(ValueError):
            simulate_trace(PowerTrace("measured?", trace.points), self.scenario,
                           period_s=60, initial_voltage_v=2)

    def test_load_csv_and_provenance(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "trace.csv"
            path.write_text(
                "elapsed_s,teg_power_uw,evidence_type\n0,1000,synthetic\n60,0,synthetic\n",
                encoding="utf-8"
            )
            t = load_power_trace(path)
            self.assertEqual(t.evidence_type, "synthetic")
            self.assertEqual(t.points[0].teg_power_w, 0.001)

    def test_mixed_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "trace.csv"
            path.write_text(
                "elapsed_s,teg_power_uw,evidence_type\n0,1000,synthetic\n60,0,measured\n",
                encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_power_trace(path)


if __name__ == "__main__":
    unittest.main()
