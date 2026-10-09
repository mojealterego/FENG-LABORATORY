import tempfile
from pathlib import Path
import unittest

from thermo_iot.bench_scpi import capture_sweep, store_records, MeterError
from thermo_iot.lab import read_sweeps, analyze_sweeps


class DummyMeter:
    def __init__(self, values):
        self.values = iter(values)
        self.commands = []

    def query(self, command):
        self.commands.append(command)
        return next(self.values)


class BenchCaptureTests(unittest.TestCase):
    def test_scpi_readings_convert_volts_amps_to_millivolts_milliamps(self):
        volts = DummyMeter(["0.010", "0.012", "0.008"])
        amps = DummyMeter(["0.0004", "0.0006", "0.0007"])
        loads = []
        records = capture_sweep(
            volts, amps, run_id="bench-01", resistances_ohm=[25, 20, 11.43],
            hot_c=65, cold_c=25,
            confirm=lambda ohms: loads.append(ohms),
            now=lambda: "2026-10-09T10:00:00Z",
        )
        self.assertEqual(loads, [25, 20, 11.43])
        self.assertEqual(volts.commands, ["MEAS:VOLT:DC?"] * 3)
        self.assertEqual(amps.commands, ["MEAS:CURR:DC?"] * 3)
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "measured.csv"
            store_records(file, records)
            report = analyze_sweeps(read_sweeps(file))
            self.assertAlmostEqual(report.runs[0].observed_peak_power_w, 7.2e-6)
            self.assertEqual(report.evidence_type, "measured")
            with self.assertRaises(FileExistsError):
                store_records(file, records)

    def test_fewer_than_three_load_points_rejected(self):
        with self.assertRaises(ValueError):
            capture_sweep(DummyMeter([]), DummyMeter([]), run_id="a",
                          resistances_ohm=[100, 200], hot_c=60, cold_c=20)

    def test_invalid_instrument_response_fails_closed(self):
        with self.assertRaises(MeterError):
            capture_sweep(
                DummyMeter(["NaN", "0.012", "0.008"]),
                DummyMeter(["0.0004", "0.0006", "0.0007"]),
                run_id="b", resistances_ohm=[25, 20, 11],
                hot_c=65, cold_c=25, confirm=lambda ohms: None,
            )

    def test_incorrect_thermal_order_rejected(self):
        with self.assertRaises(ValueError):
            capture_sweep(DummyMeter([]), DummyMeter([]), run_id="c",
                          resistances_ohm=[1, 2, 3], hot_c=20, cold_c=50)


if __name__ == "__main__":
    unittest.main()
