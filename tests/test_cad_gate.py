"""Factory readiness must never be inferred from a green diagnostics workflow."""
from pathlib import Path
import tempfile
import unittest
from hardware.cad_gate import DrcReportError, classify_drc, parse_drc_report


class ManufacturingGateTests(unittest.TestCase):
    def test_realistic_active_unrouted_board_is_blocked(self):
        raw=("** Drc report for ltc3108_power_breakout.kicad_pcb **\n"
             "** Found 13 DRC violations **\n"
             "** Found 30 unconnected items **\n")
        d=parse_drc_report(raw)
        self.assertEqual(d["violations"],13)
        self.assertEqual(d["unconnected"],30)
        verdict=classify_drc(d)
        self.assertEqual(verdict["status"],"HOLD")
        self.assertFalse(verdict["fabrication_authorized"])

    def test_clean_cad_still_needs_human_electrical_review(self):
        d=parse_drc_report("** Found 0 DRC violations **\n"
                           "** Found 0 unconnected pads **\n")
        verdict=classify_drc(d)
        self.assertEqual(verdict["status"],"ENGINEERING_REVIEW_REQUIRED")
        self.assertFalse(verdict["fabrication_authorized"])

    def test_missing_or_ambiguous_drc_counts_fail_closed(self):
        for snippet in (
            "", "** Found 0 DRC violations **\n",
            "** Found 0 unconnected items **\n",
            "** Found 0 DRC violations **\n** Found 1 DRC violations **\n"
            "** Found 0 unconnected items **\n",
            "** Found 0 DRC violations **\n** Found -1 unconnected items **\n",
        ):
            with self.subTest(snippet=snippet[:35]):
                with self.assertRaises(DrcReportError):
                    parse_drc_report(snippet)

    def test_unconnected_only_is_blocking(self):
        d=parse_drc_report("** Found 0 DRC violations **\n"
                           "** Found 2 unconnected items **\n")
        self.assertEqual(classify_drc(d)["status"],"HOLD")


if __name__=="__main__":
    unittest.main()
