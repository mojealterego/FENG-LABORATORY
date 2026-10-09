"""Physical MVP dossier must distinguish content integrity from physical truth.

Fixture 'measured' samples are explicitly invented for the tests and are NOT
real laboratory measurements or device qualification evidence.
"""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from thermo_iot.mvp_acceptance import (
    REQUIRED_ARTIFACTS, EvidenceError, create_manifest, audit_bundle,
)
from thermo_iot.lorawan_fieldtest import build_rf_test_frame, record_rf_attempt


class MvpEvidenceBundleTests(unittest.TestCase):
    def build_fixture(self, root: Path):
        (root/"teg_sweep.csv").write_text(
            "run_id,measurement_utc,hot_c,cold_c,voltage_mv,current_ma,evidence_type\n"
            "r1,2026-10-09T14:00:01Z,50,20,10,0.4,measured\n"
            "r1,2026-10-09T14:00:02Z,50,20,12,0.5,measured\n"
            "r1,2026-10-09T14:00:03Z,50,20,11,0.6,measured\n")
        (root/"pmic_profile.csv").write_text(
            "elapsed_s,vin_v,iin_a,vout_v,iout_a,vstore_v,evidence_type\n"
            "0,0.05,0.0004,0,0,0,measured\n"
            "1,0.05,0.0004,3.3,0.0001,3.05,measured\n")
        initial=datetime(2026,10,9,14,1,tzinfo=timezone.utc)
        payload=build_rf_test_frame(4300,3000,None,challenge=15)
        record_rf_attempt(
            root/"rf_attempt.json",
            modem_result={"probe_state":"radio_command_completed","network_delivery":"unverified"},
            payload=payload,
            application_id="test-lab",device_id="test-node",
            start_utc=initial,end_utc=initial+timedelta(seconds=12),
        )
        receipt={
            "end_device_ids":{
                "device_id":"test-node","application_ids":{"application_id":"test-lab"}
            },
            "received_at":"2026-10-09T14:01:16Z",
            "uplink_message":{
                "session_key_id":"fake-session",
                "f_port":10,"f_cnt":1,
                "frm_payload":base64.b64encode(payload).decode("ascii")
            },
        }
        (root/"ttn_uplink.json").write_text(json.dumps(receipt))
        (root/"active_pcb_drc.txt").write_text(
            "** Drc report for candidate **\n"
            "** Found 0 DRC violations **\n"
            "** Found 0 unconnected pads **\n"
        )
        (root/"firmware_flash.log").write_text(
            "OPERATOR PROVIDED: flash utility screenshot and board label must be reviewed\n"
        )
        (root/"autonomous_energy_trace.csv").write_text(
            "elapsed_s,teg_power_uw,evidence_type\n"
            + "".join(f"{i * 3600},500,measured\n" for i in range(169))
        )

    def test_bundle_passes_documentary_consistency_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.build_fixture(root)
            created=create_manifest(root,root/"manifest.json")
            self.assertEqual(set(created["artifacts"]),set(REQUIRED_ARTIFACTS))
            report=audit_bundle(root,root/"manifest.json")
            self.assertEqual(report["file_integrity"],"matches_manifest")
            self.assertEqual(report["physically_validated"],False)
            self.assertEqual(report["verification_level"],"documentary_consistency_only")
            self.assertTrue(report["requires_independent_hardware_signoff"])
            self.assertEqual(report["teg_evidence_type"],"measured")
            self.assertEqual(report["radio_receipt_content"],"ttn_receipt_content_matches")
            self.assertEqual(report["energy_trace_samples"], 169)
            self.assertEqual(report["energy_trace_max_gap_s"], 3600)

    def test_tampered_file_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.build_fixture(root)
            create_manifest(root,root/"manifest.json")
            with (root/"teg_sweep.csv").open("a") as file:
                file.write("r1,2026-10-09T14:00:04Z,50,20,10,0.4,measured\n")
            with self.assertRaises(EvidenceError):
                audit_bundle(root,root/"manifest.json")

    def test_synthetic_meter_data_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.build_fixture(root)
            path=root/"pmic_profile.csv"
            path.write_text(path.read_text().replace(",measured",",synthetic"))
            create_manifest(root,root/"manifest.json")
            with self.assertRaises(EvidenceError):
                audit_bundle(root,root/"manifest.json")

    def test_nonzero_cad_drc_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.build_fixture(root)
            file=root/"active_pcb_drc.txt"
            file.write_text(file.read_text().replace("0 DRC violations","30 DRC violations"))
            create_manifest(root,root/"manifest.json")
            with self.assertRaises(EvidenceError):
                audit_bundle(root,root/"manifest.json")

    def test_less_than_seven_days_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.build_fixture(root)
            file=root/"autonomous_energy_trace.csv"
            file.write_text(file.read_text().replace("604800","604799"))
            create_manifest(root,root/"manifest.json")
            with self.assertRaises(EvidenceError):
                audit_bundle(root,root/"manifest.json")


    def test_only_two_endpoint_samples_do_not_prove_seven_day_trace(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.build_fixture(root)
            (root/"autonomous_energy_trace.csv").write_text(
                "elapsed_s,teg_power_uw,evidence_type\n"
                + "0,500,measured\n"
                + "604800,500,measured\n"
            )
            create_manifest(root, root/"manifest.json")
            with self.assertRaisesRegex(EvidenceError, "sampling|coverage|gap"):
                audit_bundle(root, root/"manifest.json")

    def test_multi_hour_gap_in_energy_trace_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.build_fixture(root)
            rows=(root/"autonomous_energy_trace.csv").read_text().splitlines()
            # Keep 7 days of observations, but remove two hourly readings
            # to create a 3-hour blind interval.
            rows=[r for r in rows if not r.startswith(("360000,","363600,"))]
            (root/"autonomous_energy_trace.csv").write_text("\\n".join(rows)+"\\n")
            create_manifest(root,root/"manifest.json")
            with self.assertRaisesRegex(EvidenceError,"sampling|coverage|gap"):
                audit_bundle(root,root/"manifest.json")

    def test_manifest_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.build_fixture(root)
            create_manifest(root,root/"manifest.json")
            with self.assertRaises(FileExistsError):
                create_manifest(root,root/"manifest.json")

    def test_path_traversal_in_manifest_is_forbidden(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.build_fixture(root)
            create_manifest(root,root/"manifest.json")
            manifest=root/"manifest.json"
            payload=json.loads(manifest.read_text())
            payload["artifacts"]["teg_sweep"]["path"]="../secrets.csv"
            manifest.write_text(json.dumps(payload))
            with self.assertRaises(EvidenceError):
                audit_bundle(root,manifest)

    def test_hardcoded_expected_artifacts_are_defined(self):
        self.assertEqual(len(REQUIRED_ARTIFACTS),7)
        self.assertIn("ttn_uplink",REQUIRED_ARTIFACTS)
        self.assertIn("teg_sweep",REQUIRED_ARTIFACTS)


if __name__=="__main__":
    unittest.main()
