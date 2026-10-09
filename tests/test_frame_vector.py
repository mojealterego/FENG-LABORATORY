import unittest
from thermo_iot.telemetry import encode_frame, decode_frame


class GoldenVectorTests(unittest.TestCase):
    def test_matches_portable_c_codec(self):
        packet = encode_frame(4350, 2700, 100, flags=2)
        self.assertEqual(packet.hex(), "01fe108c0a640002")
        self.assertEqual(decode_frame(bytes.fromhex("01fe108c0a640002")).temperature_centi_c, 4350)


if __name__ == "__main__":
    unittest.main()
