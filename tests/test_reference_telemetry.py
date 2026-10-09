"""MCU die-temperature RF demo frames must never enter pipe anomaly baselines."""
import base64
from pathlib import Path
import tempfile
import unittest
from thermo_iot.telemetry import TelemetryStore,TelemetryService,encode_frame


def wire_event(index,flags=0,temperature=4300):
    return {
        "end_device_ids":{
            "application_ids":{"application_id":"research-station"},
            "device_id":"wio-e5-lab",
        },
        "received_at":f"2026-10-09T10:00:{index:02d}Z",
        "uplink_message":{
            "session_key_id":"session-123",
            "f_cnt":index+1,"f_port":10,
            "frm_payload":base64.b64encode(encode_frame(temperature,0,None,flags)).decode(),
        },
    }


class NoFalseProcessMonitoring(unittest.TestCase):
    def test_flags_0x80_is_explicitly_reference_only(self):
        with tempfile.TemporaryDirectory() as root:
            service=TelemetryService(TelemetryStore(Path(root)/"db.sqlite"))
            receipt=service.process(wire_event(0,flags=0x80))
            self.assertEqual(receipt.state,"reference_telemetry")
            self.assertEqual(service.store.summary("research-station","wio-e5-lab")["candidate_anomalies"],0)

    def test_reference_frames_are_not_anomaly_history(self):
        with tempfile.TemporaryDirectory() as root:
            service=TelemetryService(TelemetryStore(Path(root)/"db.sqlite"))
            for i in range(10):
                receipt=service.process(wire_event(i,flags=0x80,temperature=4100))
                self.assertEqual(receipt.state,"reference_telemetry")
            real=service.process(wire_event(10,flags=0x00,temperature=5500))
            self.assertEqual(real.state,"insufficient_history")
            self.assertEqual(service.store.summary("research-station","wio-e5-lab")["total"],11)

    def test_reference_candidate_is_not_process_anomaly(self):
        with tempfile.TemporaryDirectory() as root:
            service=TelemetryService(TelemetryStore(Path(root)/"db.sqlite"))
            for i in range(6):
                service.process(wire_event(i,flags=0,temperature=4100))
            probe=service.process(wire_event(6,flags=0x80,temperature=10000))
            self.assertEqual(probe.state,"reference_telemetry")


if __name__=="__main__":
    unittest.main()
