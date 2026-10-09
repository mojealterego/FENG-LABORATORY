"""KiCad netlist checks: protect Wio-E5 UART polarity and LTC3108 rails."""
import tempfile
from pathlib import Path
import unittest
from hardware.verify_kicad_netlist import (
    CARRIER, PMIC, NetlistMismatch, parse_nodes, verify_contract
)


def make_xml(mapping):
    content=["<export><nets>"]
    nets={}
    for ref,pins in mapping.items():
        for index,name in enumerate(pins,1):
            nets.setdefault(name,[]).append((ref,str(index)))
    for index,(name,positions) in enumerate(nets.items(),1):
        content.append(f'<net code="{index}" name="{name}">')
        content.extend(f'<node ref="{ref}" pin="{pin}"/>' for ref,pin in positions)
        content.append("</net>")
    content.append("</nets></export>")
    return "".join(content)


class NativeNetlistContractTests(unittest.TestCase):
    def parse(self,mapping):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/"test.xml"
            file.write_text(make_xml(mapping))
            return parse_nodes(file)

    def test_both_expected_circuits(self):
        for mapping in (CARRIER,PMIC):
            with self.subTest(kind=tuple(mapping)):
                result=verify_contract(self.parse(mapping),mapping)
                self.assertGreater(result["pads_verified"],10)
                self.assertFalse(result["hardware_proven"])

    def test_uart_tx_rx_swap_must_fail(self):
        changed=dict(CARRIER)
        changed["J3"]=("GND","MCU_TX","MCU_RX")
        with self.assertRaises(NetlistMismatch):
            verify_contract(self.parse(changed),CARRIER)

    def test_pmic_store_on_mcu_voltage_rail_must_fail(self):
        changed=dict(PMIC)
        changed["J3"]=("VSTORE","GND")
        with self.assertRaises(NetlistMismatch):
            verify_contract(self.parse(changed),PMIC)

    def test_duplicate_pin_or_unexpected_component_fails(self):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/"dups.xml"
            file.write_text('<export><nets><net name="GND"><node ref="J1" pin="1"/><node ref="J1" pin="1"/></net></nets></export>')
            with self.assertRaises(NetlistMismatch):
                parse_nodes(file)
        invalid=self.parse({**CARRIER,"Q1":("GND",)})
        with self.assertRaises(NetlistMismatch):
            verify_contract(invalid,CARRIER)

    def test_root_local_label_slash_is_normalized(self):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/"native.xml"
            file.write_text('<export><nets><net code="1" name="/GND">'
                            '<node ref="J1" pin="2"/></net></nets></export>')
            self.assertEqual(parse_nodes(file)[("J1","2")],"GND")

    def test_corrupt_empty_xml_must_fail(self):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/"invalid.xml"
            file.write_text("<export><broken></export>")
            with self.assertRaises(NetlistMismatch):
                parse_nodes(file)


if __name__=="__main__":
    unittest.main()
