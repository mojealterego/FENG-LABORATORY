"""SDK overlay staging regression tests. Build and real RF are separate gates."""
import tempfile
from pathlib import Path
import unittest
from firmware.stm32wle5jc.make_overlay import (
    IntegrationError, rewrite_app, rewrite_header, prepare_overlay, APP_DIR,
)


def vendor_source():
    return (
        '#include "lora_app.h"\n'
        "static void SendTxData(void)\n{\n"
        "  AppData.BufferSize = 1;\n"
        "  LmHandlerSend(&AppData, 0, 0, false);\n"
        "}\n"
        "\nstatic void OnTxTimerEvent(void *context)\n"
        "{ (void)context; }\n"
    )


def vendor_header():
    return (
        "#define ACTIVE_REGION LORAMAC_REGION_EU868\n"
        "#define LORAWAN_DEFAULT_ACTIVATION_TYPE ACTIVATION_TYPE_OTAA\n"
        "#define APP_TX_DUTYCYCLE 30000\n"
        "#define LORAWAN_USER_APP_PORT 2\n"
    )


class CubeIDEOverlayTests(unittest.TestCase):
    def test_rewrites_send_only_and_marks_absent_measurements(self):
        patch = rewrite_app(vendor_source())
        self.assertIn("thermo_iot_encode_frame(die_temp_centi_c, 0u, -1, 0x80u", patch)
        self.assertIn("AppData.Port = LORAWAN_USER_APP_PORT", patch)
        self.assertIn("static void OnTxTimerEvent", patch)
        self.assertNotIn("AppData.BufferSize = 1;", patch)

    def test_rejects_double_application(self):
        with self.assertRaises(IntegrationError):
            rewrite_app(rewrite_app(vendor_source()))

    def test_rewrites_only_lorawan_config_macros(self):
        output = rewrite_header(vendor_header())
        self.assertIn("APP_TX_DUTYCYCLE 600000", output)
        self.assertIn("LORAWAN_USER_APP_PORT 10", output)
        with self.assertRaises(IntegrationError):
            rewrite_header("#define APP_TX_DUTYCYCLE 30000\n")

    def test_stages_without_mutating_vendor_project(self):
        with tempfile.TemporaryDirectory() as root:
            upstream = Path(root) / "seeed"
            source_dir = upstream / APP_DIR
            source_dir.mkdir(parents=True)
            (source_dir / "lora_app.c").write_text(vendor_source())
            (source_dir / "lora_app.h").write_text(vendor_header())
            dest = Path(root) / "new-staged"
            result = prepare_overlay(upstream, dest)
            self.assertEqual(len(result["staged_files"]), 4)
            self.assertFalse(result["cross_compiled"])
            self.assertTrue((dest / "thermo_iot_frame.c").exists())
            self.assertIn("AppData.BufferSize = 1;", (source_dir / "lora_app.c").read_text())
            with self.assertRaises(FileExistsError):
                prepare_overlay(upstream, dest)

    def test_missing_vendor_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(IntegrationError):
                prepare_overlay(Path(root), Path(root) / "out")


if __name__ == "__main__":
    unittest.main()
