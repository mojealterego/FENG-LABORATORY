"""Offline LoRaWAN field-quality statistics. Fixtures are synthetic, not RF evidence."""
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from thermo_iot.rf_audit import RfAuditError, analyze_events, read_ttn_jsonl
from thermo_iot.telemetry import encode_frame


BASE = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)


def event(counter, *, seconds=0, session="sess-a", flags=0, rssi=-100, snr=4.0):
    payload=encode_frame(4300, 3000, None, flags)
    return {
        "end_device_ids": {
            "application_ids":{"application_id":"thermo-lab"},
            "device_id":"pipe-1",
        },
        "received_at":(BASE+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z"),
        "uplink_message":{
            "session_key_id":session, "f_cnt":counter, "f_port":10,
            "frm_payload":base64.b64encode(payload).decode(),
            "rx_metadata":[{"rssi":rssi,"snr":snr}],
        },
    }


class FieldMetrics(unittest.TestCase):
    def test_distinguishes_unique_packets_and_counter_gaps_from_pdr(self):
        events=[event(1),event(2,seconds=600),event(5,seconds=1200),
                event(5,seconds=1200),event(6,seconds=1800,flags=0x80)]
        r=analyze_events(events,expected_app="thermo-lab",expected_device="pipe-1")
        self.assertEqual(r["received_events"],5)
        self.assertEqual(r["unique_uplinks"],4)
        self.assertEqual(r["duplicate_events"],1)
        self.assertEqual(r["counter_discontinuity_estimate"],2)
        self.assertEqual(r["reference_lab_frames"],1)
        self.assertEqual(r["pipe_measurement_frames"],3)
        self.assertEqual(r["observed_duration_s"],1800)
        self.assertAlmostEqual(r["median_observed_gap_s"],600)
        self.assertEqual(r["median_snr_db"],4)
        self.assertNotIn("delivery_rate_percent",r)
        self.assertFalse(r["physical_reception_verified"])

    def test_session_reset_does_not_look_like_packet_loss(self):
        rows=[event(20,seconds=0),event(1,seconds=100,session="sess-b"),
              event(2,seconds=200,session="sess-b")]
        r=analyze_events(rows,expected_app="thermo-lab",expected_device="pipe-1")
        self.assertEqual(r["observed_sessions"],2)
        self.assertEqual(r["counter_discontinuity_estimate"],0)
        self.assertEqual(r["counter_regressions"],0)

    def test_out_of_order_counters_are_not_automatically_loss(self):
        r=analyze_events([event(3),event(2,seconds=60),event(4,seconds=120)],
                         expected_app="thermo-lab",expected_device="pipe-1")
        self.assertEqual(r["counter_regressions"],1)
        self.assertEqual(r["counter_discontinuity_estimate"],1)

    def test_conflicting_duplicate_counter_is_rejected(self):
        events=[event(7),event(7,seconds=5,flags=0x80)]
        with self.assertRaises(RfAuditError):
            analyze_events(events,expected_app="thermo-lab",expected_device="pipe-1")

    def test_rejects_mixed_device_and_unauthenticated_packet(self):
        packet=event(1)
        packet["end_device_ids"]["device_id"]="wrong"
        with self.assertRaises(RfAuditError):
            analyze_events([packet],expected_app="thermo-lab",expected_device="pipe-1")
        with self.assertRaises(RfAuditError):
            analyze_events([{"uplink_message":{"f_cnt":1}}],expected_app="thermo-lab",expected_device="pipe-1")

    def test_strict_jsonl_rejects_duplicate_keys_and_oversize(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ttn.jsonl"
            path.write_text(json.dumps(event(1))+"\n"+json.dumps(event(2,seconds=500))+"\n")
            values=read_ttn_jsonl(path)
            self.assertEqual(len(values),2)
            path.write_text('{"received_at":"x","received_at":"y"}\n')
            with self.assertRaises(RfAuditError):
                read_ttn_jsonl(path)
            path.write_bytes(b"x"*200)
            with self.assertRaises(RfAuditError):
                read_ttn_jsonl(path,max_bytes=100)

    def test_missing_or_invalid_rf_metadata_does_not_invent_signal_strength(self):
        clean=event(1)
        clean["uplink_message"].pop("rx_metadata")
        res=analyze_events([clean],expected_app="thermo-lab",expected_device="pipe-1")
        self.assertIsNone(res["median_rssi_dbm"])
        self.assertIsNone(res["median_snr_db"])
        broken=event(2)
        broken["uplink_message"]["rx_metadata"]=[{"rssi":True,"snr":4}]
        with self.assertRaises(RfAuditError):
            analyze_events([broken],expected_app="thermo-lab",expected_device="pipe-1")

    def test_jsonl_empty_file_is_not_a_radio_report(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ttn.jsonl"
            path.write_text("")
            with self.assertRaises(RfAuditError):
                read_ttn_jsonl(path)


if __name__=="__main__":
    unittest.main()
