import unittest

from thermo_iot.anomaly import DetectionPolicy, detect_temperature_anomaly


class TemperatureAnomalyTests(unittest.TestCase):
    def test_returns_insufficient_history_for_short_baseline(self):
        result = detect_temperature_anomaly([50.0, 50.0], 62.0)
        self.assertEqual(result.state, "insufficient_history")
        self.assertFalse(result.is_candidate)

    def test_constant_baseline_normal(self):
        result = detect_temperature_anomaly([50.0] * 6, 50.3)
        self.assertEqual(result.state, "normal")
        self.assertFalse(result.is_candidate)

    def test_temperature_spike_is_anomaly_candidate(self):
        result = detect_temperature_anomaly([50.0, 50.1, 49.9, 50.0, 50.2, 49.8], 60.0)
        self.assertTrue(result.is_candidate)
        self.assertEqual(result.state, "anomaly_candidate")

    def test_robust_against_single_bad_historic_measurement(self):
        r = detect_temperature_anomaly([50.0, 50.0, 50.1, 50.0, 100.0, 49.9, 50.0], 50.2)
        self.assertFalse(r.is_candidate)

    def test_rejects_invalid_measurement(self):
        with self.assertRaises(ValueError):
            detect_temperature_anomaly([50.0] * 6, float("nan"))

    def test_rejects_empty_policy_window(self):
        with self.assertRaises(ValueError):
            detect_temperature_anomaly([50.0] * 6, 60.0, DetectionPolicy(min_samples=0))

    def test_history_does_not_include_query_value(self):
        r = detect_temperature_anomaly([20.0] * 6, 90.0)
        self.assertAlmostEqual(r.reference_c, 20.0)


if __name__ == '__main__':
    unittest.main()
