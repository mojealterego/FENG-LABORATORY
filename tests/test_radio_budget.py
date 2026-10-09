"""Radio burst estimates: deliberately conservative and not hardware-validated."""
import math
import unittest
from thermo_iot.radio_budget import RadioBurst, estimate_burst


class RadioBudgetTests(unittest.TestCase):
    def test_87ma_high_power_tx_alone_exceeds_original_219mj(self):
        result = estimate_burst(RadioBurst())
        self.assertGreater(result.tx_energy_j, 0.0219)
        self.assertAlmostEqual(result.tx_energy_j, 3.3 * 0.087 * 0.2)

    def test_higher_esr_increases_reservoir_voltage_droop(self):
        low = estimate_burst(RadioBurst(cap_esr_ohm=0.1))
        high = estimate_burst(RadioBurst(cap_esr_ohm=1.0))
        self.assertGreater(high.worst_instantaneous_drop_v, low.worst_instantaneous_drop_v)

    def test_capacitance_reduces_long_tx_voltage_loss(self):
        low = estimate_burst(RadioBurst(capacitance_f=0.2))
        high = estimate_burst(RadioBurst(capacitance_f=5.0))
        self.assertGreater(low.reservoir_discharge_v, high.reservoir_discharge_v)

    def test_impossibly_low_reservoir_fails_voltage_screening(self):
        out = estimate_burst(RadioBurst(capacitance_f=0.01, cap_esr_ohm=1.0))
        self.assertFalse(out.above_minimum_voltage)

    def test_rejects_non_finite_or_negative_inputs(self):
        for config in (RadioBurst(tx_current_a=-1), RadioBurst(cap_esr_ohm=math.nan),
                       RadioBurst(capacitance_f=0), RadioBurst(initial_voltage_v=0)):
            with self.subTest(config=config), self.assertRaises(ValueError):
                estimate_burst(config)


if __name__ == "__main__":
    unittest.main()
