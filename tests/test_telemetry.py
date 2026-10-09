"""Contract-first tests for the Thermo-IoT reference telemetry path."""

import base64
from contextlib import redirect_stdout
from datetime import datetime, timezone
from http.client import HTTPConnection
import io
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest

from thermo_iot.gateway import build_server, main as gateway_main
from thermo_iot.telemetry import (
    TelemetryService,
    TelemetryStore,
    UplinkValidationError,
    decode_frame,
    encode_frame,
    parse_ttn_uplink,
)


def event(*, frame_counter=1, session="session-1", device="pipe-1",
          app="district-heat", temp_centi_c=4350,
          capacitor_mv=2700, teg_uw=100, received_at="2026-10-09T12:00:00Z"):
    wire = encode_frame(temp_centi_c, capacitor_mv, teg_uw, flags=2)
    return {
        "end_device_ids": {
            "device_id": device,
            "application_ids": {"application_id": app},
        },
        "received_at": received_at,
        "uplink_message": {
            "session_key_id": session,
            "f_cnt": frame_counter,
            "f_port": 10,
            "frm_payload": base64.b64encode(wire).decode("ascii"),
        },
    }


class BinaryWireTests(unittest.TestCase):
    def test_round_trip_and_length(self):
        packet = encode_frame(-1250, 3200, 900, flags=3)
        self.assertEqual(len(packet), 8)
        decoded = decode_frame(packet)
        self.assertEqual(decoded.temperature_centi_c, -1250)
        self.assertEqual(decoded.capacitor_mv, 3200)
        self.assertEqual(decoded.teg_power_uw, 900)
        self.assertEqual(decoded.flags, 3)

    def test_teg_measurement_can_be_unavailable(self):
        packet = encode_frame(2350, 2900, None)
        self.assertIsNone(decode_frame(packet).teg_power_uw)

    def test_rejects_bad_frame_version_and_length(self):
        for frame in (b"", b"12345678", b"\x01" * 7, b"\x01" * 9):
            with self.subTest(frame=frame), self.assertRaises(UplinkValidationError):
                decode_frame(frame)

    def test_rejects_out_of_range_temperature_voltage_or_power(self):
        for args in ((15001, 2500, 100), (-4001, 2500, 100),
                     (4000, 5501, 100), (4000, -1, 100),
                     (4000, 2500, 65535), (4000, 2500, -1)):
            with self.subTest(args=args), self.assertRaises(UplinkValidationError):
                encode_frame(*args)

    def test_decoder_rejects_out_of_range_encoded_temperature(self):
        wire = struct.pack("<BhHHB", 1, 21000, 2500, 100, 0)
        with self.assertRaises(UplinkValidationError):
            decode_frame(wire)


class TTNEnvelopeTests(unittest.TestCase):
    def test_valid_v3_envelope_maps_without_decoded_payload(self):
        payload = event()
        payload["uplink_message"]["decoded_payload"] = {"temperature": -99999}
        parsed = parse_ttn_uplink(payload)
        self.assertEqual(parsed.app_id, "district-heat")
        self.assertEqual(parsed.device_id, "pipe-1")
        self.assertEqual(parsed.frame_counter, 1)
        self.assertEqual(parsed.received_at, "2026-10-09T12:00:00.000000Z")
        self.assertEqual(parsed.sample.temperature_centi_c, 4350)

    def test_timezone_offset_is_normalized_to_utc(self):
        parsed = parse_ttn_uplink(event(received_at="2026-10-09T14:00:00+02:00"))
        self.assertEqual(parsed.received_at, "2026-10-09T12:00:00.000000Z")

    def test_rejects_unauthorized_fport_bad_base64_missing_session_and_boolean_counter(self):
        for mutation in ("port", "base64", "session", "boolean-counter"):
            data = event()
            if mutation == "port":
                data["uplink_message"]["f_port"] = 1
            elif mutation == "base64":
                data["uplink_message"]["frm_payload"] = "!!!="
            elif mutation == "session":
                del data["uplink_message"]["session_key_id"]
            else:
                data["uplink_message"]["f_cnt"] = True
            with self.subTest(mutation=mutation), self.assertRaises(UplinkValidationError):
                parse_ttn_uplink(data)

    def test_rejects_non_utc_naive_timestamp(self):
        with self.assertRaises(UplinkValidationError):
            parse_ttn_uplink(event(received_at="2026-10-09T12:00:00"))

    def test_rejects_bad_or_missing_application(self):
        for app in ("", "bad app!", "x" * 130):
            with self.subTest(app=app), self.assertRaises(UplinkValidationError):
                parse_ttn_uplink(event(app=app))


class TelemetryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "measurements.db"
        self.service = TelemetryService(TelemetryStore(self.path))

    def tearDown(self):
        self.tmp.cleanup()

    def test_ingestion_is_idempotent(self):
        packet = event()
        first = self.service.process(packet)
        second = self.service.process(packet)
        self.assertTrue(first.inserted)
        self.assertFalse(second.inserted)
        self.assertEqual(second.state, "duplicate")
        self.assertEqual(self.service.store.summary("district-heat", "pipe-1")["total"], 1)

    def test_new_session_with_reset_frame_counter_is_accepted(self):
        self.service.process(event(session="session-1"))
        receipt = self.service.process(event(session="session-2"))
        self.assertTrue(receipt.inserted)
        self.assertEqual(self.service.store.summary("district-heat", "pipe-1")["total"], 2)

    def test_applications_are_isolated(self):
        self.service.process(event(app="operator-a"))
        self.service.process(event(app="operator-b"))
        self.assertEqual(self.service.store.summary("operator-a", "pipe-1")["total"], 1)
        self.assertEqual(self.service.store.summary("operator-b", "pipe-1")["total"], 1)

    def test_anomaly_requires_history_and_is_only_a_candidate(self):
        for i in range(5):
            r = self.service.process(event(frame_counter=i + 1, temp_centi_c=4000,
                                           received_at=f"2026-10-09T12:00:{i:02d}Z"))
        self.assertEqual(r.state, "insufficient_history")
        r = self.service.process(event(frame_counter=6, temp_centi_c=5500,
                                       received_at="2026-10-09T12:00:06Z"))
        self.assertEqual(r.state, "anomaly_candidate")
        summary = self.service.store.summary("district-heat", "pipe-1")
        self.assertEqual(summary["candidate_anomalies"], 1)
        self.assertEqual(summary["total"], 6)

    def test_late_packet_is_stored_but_not_alerted(self):
        self.service.process(event(frame_counter=3, received_at="2026-10-09T12:03:00Z"))
        r = self.service.process(event(frame_counter=1, received_at="2026-10-09T12:01:00Z",
                                       temp_centi_c=6000))
        self.assertTrue(r.inserted)
        self.assertEqual(r.state, "out_of_order")
        self.assertEqual(self.service.store.summary("district-heat", "pipe-1")["total"], 2)

    def test_report_of_unknown_device_has_zero_total(self):
        self.assertEqual(self.service.store.summary("district-heat", "unknown")["total"], 0)


class OfflineCliTests(unittest.TestCase):
    def test_ingest_and_report_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            packet_file = path / "packet.json"
            db_file = path / "telemetry.sqlite"
            packet_file.write_text(json.dumps(event()), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = gateway_main(["ingest", "--db", str(db_file), "--file", str(packet_file)])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(out.getvalue())["inserted"])
            out = io.StringIO()
            with redirect_stdout(out):
                code = gateway_main(["report", "--db", str(db_file), "--app", "district-heat",
                                     "--device", "pipe-1"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["total"], 1)


class LocalWebhookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        service = TelemetryService(TelemetryStore(Path(self.tmp.name) / "webhook.db"))
        self.server = build_server("127.0.0.1", 0, service, token="secret-" + "x" * 32)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.tmp.cleanup()

    def request(self, body, token=None, path="/ttn/uplink"):
        conn = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        conn.request("POST", path, body=body, headers=headers)
        response = conn.getresponse()
        result = (response.status, response.read())
        conn.close()
        return result

    def test_authentication_and_idempotency(self):
        data = json.dumps(event()).encode("utf-8")
        unauthorized, _ = self.request(data)
        self.assertEqual(unauthorized, 401)
        valid, body = self.request(data, token="secret-" + "x" * 32)
        self.assertEqual(valid, 201)
        self.assertTrue(json.loads(body)["inserted"])
        dupe, body = self.request(data, token="secret-" + "x" * 32)
        self.assertEqual(dupe, 200)
        self.assertEqual(json.loads(body)["state"], "duplicate")

    def test_rejects_malformed_json_and_oversized_payload(self):
        bad, _ = self.request(b"{broken", token="secret-" + "x" * 32)
        self.assertEqual(bad, 400)
        huge, _ = self.request(b"x" * 70000, token="secret-" + "x" * 32)
        self.assertEqual(huge, 413)

    def test_blocks_unexpected_path(self):
        code, _ = self.request(json.dumps(event()).encode(), token="secret-" + "x" * 32,
                               path="/")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
