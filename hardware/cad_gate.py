"""Conservative KiCad DRC readout with an explicit NOT-FOR-FAB status.

All checks are documentary. An empty error list is not a mechanical,
electrical, safety or supply-chain release approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


class DrcReportError(ValueError):
    """Required KiCad DRC information was absent or inconsistent."""


def parse_drc_report(text: str) -> dict:
    if not isinstance(text,str) or len(text)>2_000_000:
        raise DrcReportError("Missing or oversize KiCad DRC report")
    violations=re.findall(r"\*\* Found (\d+) DRC violations \*\*",text)
    unconnected=re.findall(r"\*\* Found (\d+) unconnected (?:items|pads) \*\*",text)
    if len(violations)!=1 or len(unconnected)!=1:
        raise DrcReportError("Exactly one violations and unconnected summary required")
    v=int(violations[0])
    u=int(unconnected[0])
    if v>1_000_000 or u>1_000_000:
        raise DrcReportError("Implausibly large DRC count")
    return {"violations":v,"unconnected":u}


def classify_drc(parsed: dict) -> dict:
    if not isinstance(parsed,dict) or set(parsed)!={"violations","unconnected"}:
        raise DrcReportError("Missing DRC fields")
    if any(isinstance(n,bool) or not isinstance(n,int) or n<0 for n in parsed.values()):
        raise DrcReportError("Invalid DRC summary counts")
    blocked=parsed["violations"]>0 or parsed["unconnected"]>0
    return {
        "status":"HOLD" if blocked else "ENGINEERING_REVIEW_REQUIRED",
        "violations":parsed["violations"],
        "unconnected":parsed["unconnected"],
        "fabrication_authorized":False,
        "physical_hardware_built":False,
        "review_gates_remaining":[
            "Schematic ERC and independent electrical review",
            "Schematic-PCB net consistency and actual manufacturer footprint approval",
            "Transformer polarity, capacitor voltage/ESR, regulator rail/current limits",
            "Solder mask, assembly drawing, DFM, fabrication and test records",
            "Patent confidentiality and manufacturing partner agreement",
        ],
    }


def main(argv: list[str]|None=None) -> int:
    p=argparse.ArgumentParser(description="Conservative PCB fabrication readiness report")
    p.add_argument("--drc",required=True,type=Path)
    p.add_argument("--require-drc-clear",action="store_true",
                   help="Fail CI if reported DRC violations or unconnected pads remain")
    args=p.parse_args(argv)
    try:
        file=args.drc
        if not file.is_file() or file.stat().st_size>2_000_000:
            raise DrcReportError("DRC report missing or oversized")
        verdict=classify_drc(parse_drc_report(file.read_text(encoding="utf-8")))
    except (OSError, UnicodeError,DrcReportError) as exc:
        print(f"Manufacturing status UNKNOWN/HOLD: {exc}",file=sys.stderr)
        return 2
    print(json.dumps(verdict,indent=2))
    if args.require_drc_clear and verdict["status"]=="HOLD":
        return 3
    return 0


if __name__=="__main__":
    raise SystemExit(main())
