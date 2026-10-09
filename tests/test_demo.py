"""Proof that synthetic demonstrations never contaminate existing databases."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from thermo_iot.demo import generate_demo, main


class SyntheticDemoTests(unittest.TestCase):
    def test_generates_deterministic_synthetic_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "demo.sqlite"
            report = generate_demo(db, count=24)
            self.assertEqual(report["generated"], 24)
            self.assertEqual(report["evidence_type"], "synthetic")
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 24)
                self.assertEqual(conn.execute("SELECT COUNT(DISTINCT device_id) FROM readings").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT MIN(app_id) FROM readings").fetchone()[0], "thermo-iot-demo")

    def test_refuses_to_write_into_existing_database(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "real.sqlite"
            db.write_bytes(b"preexisting")
            with self.assertRaises(FileExistsError):
                generate_demo(db, count=12)
            self.assertEqual(db.read_bytes(), b"preexisting")

    def test_validates_sample_count(self):
        with tempfile.TemporaryDirectory() as folder:
            for count in (0, 5001, -1, True):
                with self.subTest(count=count), self.assertRaises(ValueError):
                    generate_demo(Path(folder) / "demo.sqlite", count=count)

    def test_cli_returns_structured_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["--db", str(Path(folder) / "demo.sqlite"), "--count", "18"])
            self.assertEqual(code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["generated"], 18)
            self.assertEqual(result["evidence_type"], "synthetic")


if __name__ == "__main__":
    unittest.main()
