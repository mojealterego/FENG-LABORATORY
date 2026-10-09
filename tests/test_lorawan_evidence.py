"""Real LoRaWAN uplink matching: no old JSON receipt can attest to a new RF attempt."""
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from thermo_iot.telemetry import decode_frame
from thermo_iot.lorawan_fieldtest import (
    FieldTestError,
    build_rf_test_frame,
    record_rf_attempt,
    verify_recorded_attempt,
    main,
)


class FieldEvidenceTests(unittest.TestCase):
    def test_challenge_and_reference_flag(self):
        a=build_rf_test_frame(4300,3000,None,challenge=13)
        b=build_rf_test_frame(4300,3000,None,challenge=14)
        self.assertNotEqual(a,b)
        self.assertEqual(decode_frame(a).flags,0x80|13)
        with self.assertRaises(ValueError):
            build_rf_test_frame(4300,3000,None,challenge=128)

    def test_record_never_overwrites_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"report.json"
            ts=datetime(2026,10,9,14,1,tzinfo=timezone.utc)
            sample=build_rf_test_frame(4300,3000,None,challenge=33)
            report=record_rf_attempt(
                path,modem_result={"network_delivery":"unverified","probe_state":"radio_command_completed"},
                payload=sample,application_id="thermo-lab",device_id="pipe-1",
                start_utc=ts,end_utc=ts+timedelta(seconds=20),
            )
            self.assertEqual(report["verification_state"],"pending_external_ttn_receipt")
            self.assertEqual(report["payload_hex"],sample.hex().upper())
            self.assertEqual(json.loads(path.read_text())["application_id"],"thermo-lab")
            with self.assertRaises(FileExistsError):
                record_rf_attempt(
                    path,modem_result={},payload=sample,application_id="thermo-lab",
                    device_id="pipe-1",start_utc=ts,end_utc=ts+timedelta(seconds=20))

    def _make_files(self,folder,*,received_at,challenge=24,actual_challenge=24,fcnt=8):
        t0=datetime(2026,10,9,14,1,tzinfo=timezone.utc)
        report=Path(folder)/"attempt.json"
        payload=build_rf_test_frame(4300,3000,None,challenge=challenge)
        record_rf_attempt(
            report,modem_result={"network_delivery":"unverified","probe_state":"radio_command_completed"},
            payload=payload,application_id="thermo-lab",device_id="pipe-1",
            start_utc=t0,end_utc=t0+timedelta(seconds=20),
        )
        actual=build_rf_test_frame(4300,3000,None,challenge=actual_challenge)
        receipt=Path(folder)/"ttn.json"
        receipt.write_text(json.dumps({
            "end_device_ids":{"device_id":"pipe-1","application_ids":{"application_id":"thermo-lab"}},
            "received_at":received_at,
            "uplink_message":{"session_key_id":"session-123","f_cnt":fcnt,"f_port":10,
                "frm_payload":base64.b64encode(actual).decode("ascii")},
        }))
        return report,receipt

    def test_receipt_from_matching_send_window_passes_offline(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b=self._make_files(folder,received_at="2026-10-09T14:01:15Z")
            result=verify_recorded_attempt(a,b)
            self.assertEqual(result["delivery_state"],"ttn_receipt_content_matches")
            self.assertIn("external",result["evidence_warning"])

    def test_stale_receipt_and_wrong_challenge_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b=self._make_files(folder,received_at="2026-10-09T13:01:15Z")
            with self.assertRaises(FieldTestError):
                verify_recorded_attempt(a,b)
            b.write_text(b.read_text().replace("13:01:15","14:01:15"))
            with self.assertRaises(FieldTestError):
                a2,b2=self._make_files(folder,received_at="2026-10-09T14:01:15Z",
                                      challenge=24,actual_challenge=25)
                verify_recorded_attempt(a2,b2)

    def test_unrelated_original_report_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b=self._make_files(folder,received_at="2026-10-09T14:01:15Z")
            altered=json.loads(a.read_text())
            altered["verification_state"]="ttn_receipt_content_matches"
            a.write_text(json.dumps(altered))
            with self.assertRaises(FieldTestError):
                verify_recorded_attempt(a,b)

    def test_verification_mode_never_opens_serial_and_requires_report(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b=self._make_files(folder,received_at="2026-10-09T14:01:15Z")
            with patch("builtins.print"):
                self.assertEqual(main(["--verify-report",str(a),"--ttn-receipt",str(b)]),0)
                self.assertEqual(main(["--ttn-receipt",str(b)]),2)
                self.assertEqual(main(["--port","COM3","--send","--ttn-receipt",str(b)]),2)


if __name__=="__main__":
    unittest.main()
