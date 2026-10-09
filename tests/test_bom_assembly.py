"""Exclude optional capacitor C7 consistently from schematic/BOM and PCB assembly.

C7 remains a physical unpopulated footprint in the candidate board. No
production approval, selected capacitor or field operation is implied.
"""
import csv
from pathlib import Path
import re
import unittest


ROOT=Path(__file__).resolve().parents[1]/"hardware/active_power"


class AssemblyDnpContractTests(unittest.TestCase):
    def test_optional_vstore_capacitor_is_assembly_dnp_everywhere(self):
        sch=(ROOT/"ltc3108_power_breakout.kicad_sch").read_text()
        board=(ROOT/"ltc3108_power_breakout.kicad_pcb").read_text()
        with (ROOT/"bom_candidate.csv").open(newline="") as f:
            rows={r["Ref"]:r for r in csv.DictReader(f)}
        self.assertIn("C7",rows)
        self.assertIn("DNP",rows["C7"]["Value/Specification"])
        c7_sch=re.search(
            r'\(symbol \(lib_id "ThermoActive:Cap"\).*?\(property "Reference" "C7"'
            r'.*?(?=\(symbol \(lib_id|\(text "LAB ONLY)',
            sch,re.DOTALL,
        )
        # Schematic C7 uses a (dnp yes) field; match it with component block.
        self.assertIsNotNone(c7_sch)
        self.assertIn("(dnp yes)",c7_sch.group(0))
        c7_board=re.search(
            r'\(footprint "ThermoActive:RadialCap".*?\(property "Reference" "C7"'
            r'.*?(?=\(footprint |\n\(segment |\n\(via |\n\(gr_line )',
            board,re.DOTALL,
        )
        self.assertIsNotNone(c7_board)
        self.assertRegex(c7_board.group(0),r'\(attr [^)]*\bdnp\b[^)]*\)')
        self.assertIn('(net 3 "VSTORE")',c7_board.group(0))
        self.assertIn('(net 1 "GND")',c7_board.group(0))

    def test_c6_storage_cap_remains_populated_not_dnp(self):
        pcb=(ROOT/"ltc3108_power_breakout.kicad_pcb").read_text()
        c6=pcb.split('(property "Reference" "C6"',1)[1].split('(footprint ',1)[0]
        self.assertNotRegex(c6,r'\(attr [^)]*\bdnp\b')


if __name__=="__main__":
    unittest.main()
