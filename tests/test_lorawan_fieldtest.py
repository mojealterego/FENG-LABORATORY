import base64
import json
from pathlib import Path
import tempfile
import unittest

from thermo_iot.lorawan_fieldtest import (
    FieldTestError, issue_command, run_probe, verify_network_receipt,
)
from thermo_iot.telemetry import encode_frame


class FakePort:
    def __init__(self, responses):
        self.responses = responses
        self.sent = []
        self.lines = []

    def reset_input_buffer(self):
        self.lines = []

    def write(self, command):
        self.sent.append(command.decode().strip())
        self.lines = list(self.responses.get(self.sent[-1], []))
        return len(command)

    def flush(self):
        return None

    def readline(self, size=256):
        if self.lines:
            return (self.lines.pop(0) + "\r\n").encode()
        raise FieldTestError("Fake modem had no completion line")


class ModemFieldTest(unittest.TestCase):
    def setUp(self):
        self.responses = {
            "AT": ["+AT: OK"],
            "AT+DR=EU868": ["+DR: EU868 DR0"],
            "AT+MODE=LWOTAA": ["+MODE: LWOTAA"],
            "AT+PORT=10": ["+PORT: 10"],
            "AT+JOIN": ["+JOIN: Start", "+JOIN: Network joined", "+JOIN: Done"],
        }

    def test_configuration_only_no_rf(self):
        port = FakePort(self.responses)
        report = run_probe(port, send=False)
        self.assertEqual(report["probe_state"], "configured_no_transmission")
        self.assertEqual(len(port.sent), 4)

    def test_join_and_hex_uplink(self):
        payload = encode_frame(4300, 3000, None)
        self.responses['AT+MSGHEX="' + payload.hex().upper() + '"'] = [
            "+MSGHEX: Start", "+MSGHEX: Done"
        ]
        port = FakePort(self.responses)
        report = run_probe(port, send=True, sample=payload)
        self.assertEqual(report["probe_state"], "radio_command_completed")
        self.assertEqual(report["network_delivery"], "unverified")
        self.assertEqual(port.sent[4], "AT+JOIN")
        self.assertEqual(port.sent[5], 'AT+MSGHEX="' + payload.hex().upper() + '"')

    def test_rejects_failed_otaa(self):
        self.responses["AT+JOIN"] = ["+JOIN: Join failed"]
        with self.assertRaises(FieldTestError):
            run_probe(FakePort(self.responses), send=True, sample=b"\x01" * 8)

    def test_rejects_send_without_binary_frame(self):
        with self.assertRaises(ValueError):
            run_probe(FakePort(self.responses), send=True)

    def test_bad_command_is_rejected(self):
        with self.assertRaises(FieldTestError):
            issue_command(FakePort(self.responses), "AT+RESET\nAT+KEY=APPKEY", "+AT:", 5)

    def test_accepts_authenticated_server_receipt_content(self):
        payload = encode_frame(4300, 3000, None)
        event = {
            "end_device_ids": {
                "device_id": "thermo-test",
                "application_ids": {"application_id": "thermo-lab"},
            },
            "received_at": "2026-10-09T10:00:00Z",
            "uplink_message": {
                "session_key_id": "session-1", "f_port": 10, "f_cnt": 11,
                "frm_payload": base64.b64encode(payload).decode(),
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "ttn.json"
            file.write_text(json.dumps(event), encoding="utf-8")
            result = verify_network_receipt(file, expected_payload=payload,
                                            application_id="thermo-lab", device_id="thermo-test")
            self.assertEqual(result["delivery_state"], "ttn_receipt_content_matches")
            with self.assertRaises(FieldTestError):
                verify_network_receipt(file, expected_payload=payload,
                                       application_id="wrong", device_id="thermo-test")


if __name__ == "__main__":
    unittest.main()
