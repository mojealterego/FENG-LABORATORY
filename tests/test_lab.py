"""Offline bench power-sweep analysis: never confuse synthetic fixtures with lab evidence."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from thermo_iot.lab import LabValidationError, analyze_sweeps, main as lab_main, read_sweeps


HEADER = "run_id,measurement_utc,hot_c,cold_c,voltage_mv,current_ma,evidence_type\n"
ROWS = [
    "run-a,2026-10-09T10:00:00Z,65,25,10,0.4,synthetic",
    "run-a,2026-10-09T10:00:01Z,65,25,12,0.6,synthetic",
    "run-a,2026-10-09T10:00:02Z,65,25,8,0.7,synthetic",
    "run-b,2026-10-09T10:01:00Z,65,25,10,0.4,synthetic",
    "run-b,2026-10-09T10:01:01Z,65,25,12,0.5,synthetic",
    "run-b,2026-10-09T10:01:02Z,65,25,8,0.7,synthetic",
]


class LabSweepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "sweep.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, lines=None):
        self.file.write_text(HEADER + "\n".join(ROWS if lines is None else lines) + "\n",
                             encoding="utf-8")
        return self.file

    def test_extracts_peak_power_from_real_voltage_current_multiplication(self):
        runs = read_sweeps(self.write())
        report = analyze_sweeps(runs)
        self.assertEqual(report.evidence_type, "synthetic")
        self.assertEqual(report.run_count, 2)
        self.assertAlmostEqual(report.runs[0].observed_peak_power_w, 7.2e-6)
        self.assertEqual(report.runs[0].voltage_at_peak_mv, 12.0)
        self.assertEqual(report.runs[0].current_at_peak_ma, 0.6)

    def test_correctly_computes_hot_to_cold_delta_in_kelvin(self):
        report = analyze_sweeps(read_sweeps(self.write()))
        self.assertAlmostEqual(report.runs[0].median_delta_t_k, 40.0)

    def test_exposes_sweep_thermal_drift_as_warning(self):
        lines = list(ROWS)
        lines[2] = lines[2].replace(",65,25,", ",68,25,")
        report = analyze_sweeps(read_sweeps(self.write(lines)))
        self.assertTrue(report.runs[0].thermal_drift_warning)

    def test_rejects_negative_current_instead_of_silently_taking_absolute_value(self):
        lines = list(ROWS)
        lines[1] = lines[1].replace(",12,0.6,", ",12,-0.6,")
        with self.assertRaises(LabValidationError):
            read_sweeps(self.write(lines))

    def test_rejects_non_finite_measurements(self):
        lines = list(ROWS)
        lines[1] = lines[1].replace(",12,0.6,", ",NaN,0.6,")
        with self.assertRaises(LabValidationError):
            read_sweeps(self.write(lines))

    def test_rejects_non_positive_temperature_gradient(self):
        lines = list(ROWS)
        lines[1] = lines[1].replace(",65,25,", ",25,65,")
        with self.assertRaises(LabValidationError):
            read_sweeps(self.write(lines))

    def test_rejects_mixed_synthetic_and_measured_evidence(self):
        lines = list(ROWS)
        lines[-1] = lines[-1].replace("synthetic", "measured")
        with self.assertRaises(LabValidationError):
            analyze_sweeps(read_sweeps(self.write(lines)))

    def test_rejects_sweep_with_less_than_three_points(self):
        lines = [x for x in ROWS if not x.startswith("run-b")]
        lines = lines[:-1]
        with self.assertRaises(LabValidationError):
            analyze_sweeps(read_sweeps(self.write(lines)))

    def test_rejects_incomplete_schema(self):
        self.file.write_text("run_id,hot_c\na,50\n", encoding="utf-8")
        with self.assertRaises(LabValidationError):
            read_sweeps(self.file)

    def test_rejects_duplicate_csv_header_fields(self):
        text = HEADER.replace("run_id,", "run_id,run_id,")
        self.file.write_text(text + "a,a,2026-10-09T10:00:00Z,65,25,10,1,synthetic\n",
                             encoding="utf-8")
        with self.assertRaises(LabValidationError):
            read_sweeps(self.file)

    def test_rejects_unbounded_csv_file(self):
        self.write()
        with self.assertRaises(LabValidationError):
            read_sweeps(self.file, max_bytes=1)

    def test_cli_emits_structured_json_with_explicit_synthetic_label(self):
        self.write()
        output = io.StringIO()
        with redirect_stdout(output):
            code = lab_main(["--file", str(self.file)])
        self.assertEqual(code, 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["evidence_type"], "synthetic")
        self.assertAlmostEqual(data["median_observed_peak_power_w"], 6.6e-6)


if __name__ == "__main__":
    unittest.main()
