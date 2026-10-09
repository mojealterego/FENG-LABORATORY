"""Static consistency checks only: they are NOT KiCad ERC/DRC."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "hardware" / "kicad"


def balanced_sexpr(text: str) -> bool:
    depth, in_string, escape = 0, False, False
    for character in text:
        if escape:
            escape = False
        elif in_string and character == "\\":
            escape = True
        elif character == '"':
            in_string = not in_string
        elif not in_string and character == "(":
            depth += 1
        elif not in_string and character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_string


class KiCadSources(unittest.TestCase):
    def test_all_native_files_are_balanced(self):
        files = [
            ROOT / "thermo_bench_carrier.kicad_sch",
            ROOT / "thermo_bench_carrier.kicad_pcb",
            ROOT / "fp-lib-table",
            *sorted((ROOT / "ThermoBench.pretty").glob("*.kicad_mod")),
        ]
        self.assertEqual(len(files), 6)
        for file in files:
            with self.subTest(file=file):
                self.assertTrue(balanced_sexpr(file.read_text(encoding="utf-8")))

    def test_connector_refs_and_isolated_measurement_nets(self):
        board = (ROOT / "thermo_bench_carrier.kicad_pcb").read_text()
        schematic = (ROOT / "thermo_bench_carrier.kicad_sch").read_text()
        for reference in ("J1", "J2", "J3", "J4", "J5"):
            self.assertIn(f'(property "Reference" "{reference}"', board)
            self.assertIn(f'(property "Reference" "{reference}"', schematic)
        for net in ("+3V3_EXT", "GND", "MCU_TX", "MCU_RX", "TEG_P",
                    "TEG_N", "PMIC_VOUT", "PMIC_RETURN"):
            self.assertIn(f'"{net}"', board)
            self.assertIn(f'"{net}"', schematic)
        segments = re.findall(r'\(segment .*?\(net (\d+)\)', board)
        self.assertEqual(len(segments), 10)
        # No physical traces to/from TEG and PMIC test connectors.
        net_index = {name: match for match, name in re.findall(r'\(net (\d+) "([^"]+)"\)', board)}
        for measurement_net in ("TEG_P", "TEG_N", "PMIC_VOUT", "PMIC_RETURN"):
            self.assertNotIn(net_index[measurement_net], segments)


if __name__ == "__main__":
    unittest.main()
