"""Verify project-local symbol tables are committed and match placed symbols.

This catches missing sources; actual KiCad ERC/DRC must run in the CAD audit.
"""
from pathlib import Path
import re
import unittest


class LocalLibraries(unittest.TestCase):
    def test_lib_and_symbol_tables_exist_for_every_project(self):
        root=Path(__file__).resolve().parents[1]
        for directory,lib,expected in (
            ("hardware/kicad","ThermoBench",("BenchConn_01x02","BenchConn_01x03","BenchConn_01x04")),
            ("hardware/active_power","ThermoActive",("LTC3108_GN16","Conn2","Conn4","Cap")),
        ):
            with self.subTest(directory=directory):
                folder=root/directory
                self.assertTrue((folder/"sym-lib-table").is_file())
                self.assertTrue((folder/"fp-lib-table").is_file())
                sym=(folder/(lib+".kicad_sym")).read_text()
                schematic=next(folder.glob("*.kicad_sch")).read_text()
                self.assertIn("(kicad_symbol_lib ",sym)
                for name in expected:
                    self.assertIn('(symbol "'+name+'"',sym)
                    self.assertIn('(symbol "'+lib+":"+name+'"',schematic)
                self.assertNotIn('(symbol "'+lib+":",sym)


if __name__=="__main__":
    unittest.main()
