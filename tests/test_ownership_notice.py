"""Regression checks for the explicitly requested proprietary ownership notice."""
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]
BRAND="Mojeaterego"
AUTHOR="Andrzej Mikulski"
EMAIL="mojealterego21@gmail.com"
PHONE="+48 455 575 337"


class RightsAndContacts(unittest.TestCase):
    def test_repo_license_lists_owner_and_no_unintended_grant(self):
        licence=(ROOT/"LICENSE").read_text(encoding="utf-8")
        for fragment in (BRAND,AUTHOR,EMAIL,PHONE,
                         "All rights reserved", "Wszelkie prawa zastrzeżone",
                         "third-party materials"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment,licence)

    def test_public_surfaces_show_authorized_contact(self):
        for file in ("README.md","docs/WNIOSEK_THERMO_IOT.md",
                     "thermo_iot/static/index.html"):
            content=(ROOT/file).read_text(encoding="utf-8")
            with self.subTest(file=file):
                for word in (BRAND,AUTHOR,EMAIL,PHONE):
                    self.assertIn(word,content)

    def test_both_schematic_and_pcb_sources_identify_owner(self):
        for stem,dir in (
            ("thermo_bench_carrier","hardware/kicad"),
            ("ltc3108_power_breakout","hardware/active_power"),
        ):
            with self.subTest(stem=stem):
                sch=(ROOT/dir/(stem+".kicad_sch")).read_text(encoding="utf-8")
                pcb=(ROOT/dir/(stem+".kicad_pcb")).read_text(encoding="utf-8")
                self.assertIn("Mojeaterego - Andrzej Mikulski",sch)
                self.assertIn("MOJEATEREGO (C) 2026 A. MIKULSKI",pcb)
                self.assertIn("(justify mirror)",pcb)


if __name__=="__main__":
    unittest.main()
