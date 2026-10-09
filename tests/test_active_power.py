"""Static KiCad pin-to-net reference checks, not KiCad ERC or PCB DRC."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "hardware" / "active_power"


class PowerSchematicTests(unittest.TestCase):
    def test_kicad_files_present_with_candidate_markings(self):
        schematic = (ROOT / "ltc3108_power_breakout.kicad_sch").read_text()
        board = (ROOT / "ltc3108_power_breakout.kicad_pcb").read_text()
        self.assertIn('(lib_id "ThermoActive:LTC3108_GN16")', schematic)
        self.assertIn('LTC3108EGN', board)
        self.assertIn('UNROUTED', board)
        self.assertEqual(len(re.findall(r'\(segment ', board)), 0)

    def test_all_16_pins_and_selected_power_nets(self):
        pcb = (ROOT / "ltc3108_power_breakout.kicad_pcb").read_text()
        start = pcb.index('(footprint "ThermoActive:SSOP16_P0635"')
        stop = pcb.index('(footprint ', start+2)
        section = pcb[start:stop]
        expected = {
            1:"GND",2:"VAUX",3:"VSTORE",4:"VOUT",5:"NC_VOUT2",
            6:"VLDO",7:"PGD",8:"GND",9:"GND",10:"GND",
            11:"VAUX",12:"GND",13:"PMIC_C1",14:"PMIC_C2",
            15:"SW",16:"GND",
        }
        matches = re.findall(r'\(pad "(\d+)" .+? \(net \d+ "([^"]+)"\)', section)
        self.assertEqual(len(matches), 16)
        self.assertEqual({int(n):net for n,net in matches}, expected)

    def test_input_output_and_storage_isolation(self):
        pcb=(ROOT / "ltc3108_power_breakout.kicad_pcb").read_text()
        nets=set(re.findall(r'\(net \d+ "([^"]+)"\)',pcb))
        self.assertIn("VOUT",nets)
        self.assertIn("VSTORE",nets)
        self.assertIn("TEG_P",nets)
        self.assertNotIn("VSTORE_3V3",nets)

    def test_bom_discloses_external_transformer(self):
        bom=(ROOT / "bom_candidate.csv").read_text()
        self.assertIn("LPR6235-752SML",bom)
        self.assertIn("NOT ON PCB",bom)


if __name__=="__main__":
    unittest.main()
