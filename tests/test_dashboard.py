"""Read-only localhost dashboard contract over the gateway SQLite schema."""
from http.client import HTTPConnection
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from thermo_iot.dashboard import DashboardRepository, build_server


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "data.sqlite"
        with sqlite3.connect(self.path) as conn:
            conn.executescript("""
              CREATE TABLE readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                session_key_id TEXT NOT NULL,
                frame_counter INTEGER NOT NULL,
                received_at TEXT NOT NULL,
                temperature_centi_c INTEGER NOT NULL,
                capacitor_mv INTEGER NOT NULL,
                teg_power_uw INTEGER,
                flags INTEGER NOT NULL,
                state TEXT NOT NULL
              );
              INSERT INTO readings (app_id, device_id, session_key_id, frame_counter, received_at,
                temperature_centi_c, capacitor_mv, teg_power_uw, flags, state)
                VALUES ('district-heat','pipe-1','s',1,'2026-10-09T12:00:00Z',4100,2800,100,0,'normal');
              INSERT INTO readings (app_id, device_id, session_key_id, frame_counter, received_at,
                temperature_centi_c, capacitor_mv, teg_power_uw, flags, state)
                VALUES ('district-heat','pipe-1','s',2,'2026-10-09T12:01:00Z',5200,2700,NULL,0,'anomaly_candidate');
              INSERT INTO readings (app_id, device_id, session_key_id, frame_counter, received_at,
                temperature_centi_c, capacitor_mv, teg_power_uw, flags, state)
                VALUES ('district-heat','pipe-2','s',1,'2026-10-09T12:00:00Z',4400,3000,50,0,'normal');
            """)
        self.repository = DashboardRepository(self.path)
        self.server = build_server("127.0.0.1", 0, self.repository)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=4)
        self.server.server_close()
        self.tmp.cleanup()

    def get(self, path):
        conn = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        conn.request("GET", path)
        resp = conn.getresponse()
        result = (resp.status, dict(resp.getheaders()), resp.read())
        conn.close()
        return result

    def test_groups_devices_and_counts_candidates(self):
        devices = self.repository.devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["app_id"], "district-heat")
        self.assertEqual(devices[0]["device_id"], "pipe-1")
        self.assertEqual(devices[0]["total"], 2)
        self.assertEqual(devices[0]["candidate_anomalies"], 1)

    def test_history_is_ascending_for_chart_with_limit_applied_to_recent_samples(self):
        history = self.repository.history("district-heat", "pipe-1", limit=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["temperature_c"], 52.0)
        full = self.repository.history("district-heat", "pipe-1", limit=2)
        self.assertEqual([x["temperature_c"] for x in full], [41.0, 52.0])

    def test_api_devices(self):
        status, headers, body = self.get("/api/devices")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(len(json.loads(body)["devices"]), 2)

    def test_api_history(self):
        status, _, body = self.get("/api/history?app=district-heat&device=pipe-1&limit=2")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["history"]), 2)

    def test_prohibits_bad_sql_identifiers_and_limit(self):
        for path in (
            "/api/history?app=district-heat&device=pipe%27-1",
            "/api/history?app=district-heat&device=pipe-1&limit=99999",
            "/api/history?app=district-heat&device=pipe-1&limit=hello",
            "/api/history?app=district-heat&device=pipe-1&limit=0",
            "/api/history?app=district-heat&device=pipe-1&limit=5&limit=6",
        ):
            with self.subTest(path=path):
                status, _, _ = self.get(path)
                self.assertEqual(status, 400)

    def test_static_ui_and_no_external_binding(self):
        status, headers, html = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Thermo-IoT", html)
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("nosniff", headers["X-Content-Type-Options"])
        status, _, script = self.get("/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"fetch", script)
        with self.assertRaises(ValueError):
            build_server("0.0.0.0", 0, self.repository)

    def test_no_write_operations_or_path_escape(self):
        status, _, _ = self.get("/../../../etc/passwd")
        self.assertEqual(status, 404)
        conn = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        conn.request("POST", "/api/devices", body=b"{}")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 405)
        resp.read()
        conn.close()


if __name__ == "__main__":
    unittest.main()
