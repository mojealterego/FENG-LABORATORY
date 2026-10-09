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
        self.assertIn('PARTIAL ROUTE', board)
        self.assertGreaterEqual(len(re.findall(r'\(segment ', board)), 6)

    def test_charge_pump_capacitors_have_real_track_endpoints(self):
        board=(ROOT / "ltc3108_power_breakout.kicad_pcb").read_text()
        # C1.2 -> U1.13 and C2.2 -> U1.14 on the existing
        # manufacturer's reference harvester breakout, not a novel circuit.
        for net,start,end in (
            (8,"59.1 17","48.6 35.6825"),
            (9,"59.1 24","48.6 35.0475"),
        ):
            segments=re.findall(
                r'\(segment \(start ([\d.]+) ([\d.]+)\) '
                r'\(end ([\d.]+) ([\d.]+)\) .*?'
                r'\(layer "F.Cu"\) \(net '+str(net)+r'\)',
                board,
            )
            self.assertGreaterEqual(len(segments),3)
            coords=[(a,b) for item in segments for a,b in ((item[0],item[1]),(item[2],item[3]))]
            self.assertIn(tuple(start.split()),coords)
            self.assertIn(tuple(end.split()),coords)


    def test_transformer_secondary_reaches_both_charging_capacitors(self):
        """Check a real two-layer conductive graph, not mere net names.

        The existing vendor LTC3108 secondary is J2.3 to C1.1/C2.1.
        Referenced by datasheet, not a new confidential product feature.
        """
        board=(ROOT / "ltc3108_power_breakout.kicad_pcb").read_text()
        links={}
        def connect(left,right):
            links.setdefault(left,set()).add(right)
            links.setdefault(right,set()).add(left)
        for ax,ay,bx,by,layer in re.findall(
            r'\(segment \(start ([\d.]+) ([\d.]+)\) '
            r'\(end ([\d.]+) ([\d.]+)\) '
            r'\(width [\d.]+\) \(layer "(F.Cu|B.Cu)"\) \(net 12\)',board
        ):
            connect((layer,float(ax),float(ay)),(layer,float(bx),float(by)))
        via_matches=re.findall(
            r'\(via \(at ([\d.]+) ([\d.]+)\).*?\(net 12\)',board
        )
        self.assertGreaterEqual(len(via_matches),2)
        for x,y in via_matches:
            connect(("F.Cu",float(x),float(y)),("B.Cu",float(x),float(y)))
        def reachable(start,goal):
            seen={start}
            stack=[start]
            while stack:
                item=stack.pop()
                if item==goal:
                    return True
                for neighbor in links.get(item,()):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            return False
        j2=("B.Cu",15.0,47.08)
        self.assertTrue(reachable(("F.Cu",56.9,17.0),j2))
        self.assertTrue(reachable(("F.Cu",56.9,24.0),j2))

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
