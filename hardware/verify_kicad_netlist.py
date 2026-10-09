"""Validate native KiCad XML NETLIST connections against a reviewed interface contract.

This verifies source connectivity for a modular laboratory candidate; it is
not a replacement for ERC/DRC, simulator, manufacturing or power-on checks.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


CARRIER={
    "J1":("+3V3_EXT","GND"),
    "J2":("+3V3_EXT","GND","MCU_TX","MCU_RX"),
    "J3":("GND","MCU_RX","MCU_TX"),
    "J4":("TEG_P","TEG_N"),
    "J5":("PMIC_VOUT","PMIC_RETURN"),
}
PMIC={
    "U1":("GND","VAUX","VSTORE","VOUT","NC_VOUT2","VLDO","PGD",
          "GND","GND","GND","VAUX","GND","PMIC_C1","PMIC_C2","SW","GND"),
    "J1":("TEG_P","GND"),
    "J2":("TEG_P","SW","SEC_HI","GND"),
    "J3":("VOUT","GND"),
    "J4":("VSTORE","GND"),
    "J5":("PGD","GND"),
    "C1":("SEC_HI","PMIC_C1"),
    "C2":("SEC_HI","PMIC_C2"),
    "C3":("VAUX","GND"),
    "C4":("VLDO","GND"),
    "C5":("TEG_P","GND"),
    "C6":("VOUT","GND"),
    "C7":("VSTORE","GND"),
}


class NetlistMismatch(ValueError):
    pass


def parse_nodes(xml_file: str|Path) -> dict[tuple[str,str],str]:
    """Read KiCad XML netlist. Duplicate pad assignment is a hard error."""
    try:
        tree=ET.parse(xml_file)
    except ET.ParseError as exc:
        raise NetlistMismatch("Invalid KiCad XML netlist") from exc
    root=tree.getroot()
    if root.tag!="export":
        raise NetlistMismatch("Expected KiCad <export> root")
    nets=root.find("nets")
    if nets is None:
        raise NetlistMismatch("No <nets> collection")
    result={}
    for net in nets.findall("net"):
        name=net.get("name")
        if not name:
            raise NetlistMismatch("A net has no name")
        # KiCad XML qualifies local labels on the root schematic with '/'.
        # These single-sheet projects have no child sheets. Keep deeper
        # hierarchical paths (if ever introduced) explicit and different.
        if name.startswith("/") and name.count("/") == 1:
            name=name[1:]
        for node in net.findall("node"):
            reference,pin=node.get("ref"),node.get("pin")
            if not reference or not pin:
                raise NetlistMismatch("Node without component ref/pin")
            key=(reference,pin)
            if key in result:
                raise NetlistMismatch(f"Duplicate assignment for {reference}.{pin}")
            result[key]=name
    if not result:
        raise NetlistMismatch("Empty netlist")
    return result


def verify_contract(nodes:dict[tuple[str,str],str],expected:dict[str,tuple[str,...]]) -> dict:
    errors=[]
    for reference,nets in expected.items():
        for index,net_name in enumerate(nets,1):
            observed=nodes.get((reference,str(index)))
            if observed!=net_name:
                errors.append(f"{reference}.{index}: expected {net_name}, observed {observed}")
    required=set(expected)
    extras=sorted(set(ref for ref,pin in nodes)-required)
    if extras:
        errors.append(f"Unexpected component references: {', '.join(extras)}")
    if errors:
        raise NetlistMismatch("; ".join(errors))
    return {
        "components":len(expected),
        "pads_verified":sum(len(pins) for pins in expected.values()),
        "net_labels":sorted(set(nodes.values())),
        "electrical_rule_check":"separate",
        "pcb_design_rule_check":"separate",
        "hardware_proven":False,
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Check KiCad XML schematic netlist")
    parser.add_argument("--kind",choices=("carrier","ltc3108"),required=True)
    parser.add_argument("--xml",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        expected=CARRIER if args.kind=="carrier" else PMIC
        report=verify_contract(parse_nodes(args.xml),expected)
    except (OSError,NetlistMismatch) as exc:
        print(f"NETLIST CONTRACT FAILURE: {exc}",file=sys.stderr)
        return 2
    print(json.dumps({"target":args.kind,**report},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
