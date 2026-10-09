"""PMIC bench capture and signed-off analysis boundary.

Physical capture requires FIVE independent SCPI-capable calibrated instruments:
Vin, Iin, Vout, Iout, Vstore. These readings occur sequentially and cannot
provide true conversion efficiency while the storage capacitor charges.
"""
import argparse
import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

HEADER=("elapsed_s","vin_v","iin_a","vout_v","iout_a","vstore_v","evidence_type")


class PmicValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PmicPoint:
    elapsed_s: float
    vin_v: float
    iin_a: float
    vout_v: float
    iout_a: float
    vstore_v: float

    @property
    def input_power_w(self):
        return self.vin_v*self.iin_a

    @property
    def output_power_w(self):
        return self.vout_v*self.iout_a


def _finite(value, name, minimum=0.0, maximum=1000.0):
    try:
        v=float(value)
    except (ValueError, TypeError) as exc:
        raise PmicValidationError(f"Invalid {name}") from exc
    if not math.isfinite(v) or v<minimum or v>maximum:
        raise PmicValidationError(f"{name} outside [{minimum}, {maximum}]")
    return v


def read_pmic_csv(path: str|Path, *, max_bytes:int=5_000_000):
    source=Path(path)
    if source.stat().st_size>max_bytes:
        raise PmicValidationError("CSV too large")
    points=[]
    sources=set()
    with source.open("r",encoding="utf-8-sig",newline="") as fp:
        reader=csv.DictReader(fp,strict=True)
        if tuple(reader.fieldnames or ())!=HEADER:
            raise PmicValidationError("Unexpected CSV header or duplicate columns")
        try:
            for row in reader:
                if None in row or any(v is None or v.strip()=="" for v in row.values()):
                    raise PmicValidationError("Missing CSV field")
                sources.add(row["evidence_type"])
                points.append(PmicPoint(
                    _finite(row["elapsed_s"],"elapsed_s",0,1e8),
                    _finite(row["vin_v"],"vin_v",0,15),
                    _finite(row["iin_a"],"iin_a",0,10),
                    _finite(row["vout_v"],"vout_v",0,10),
                    _finite(row["iout_a"],"iout_a",0,10),
                    _finite(row["vstore_v"],"vstore_v",0,10),
                ))
                if len(points)>50000:
                    raise PmicValidationError("CSV exceeds 50000 rows")
        except csv.Error as exc:
            raise PmicValidationError("Malformed CSV") from exc
    if len(points)<2 or sources not in ({"synthetic"},{"measured"}):
        raise PmicValidationError("Requires at least 2 rows with one valid evidence_type")
    for prev,curr in zip(points,points[1:]):
        if curr.elapsed_s<=prev.elapsed_s:
            raise PmicValidationError("PMIC timestamps must increase strictly")
    return next(iter(sources)),tuple(points)


def analyze_pmic(points:tuple[PmicPoint,...],evidence_type:str,*,start_v:float=0.1,target_v:float=3.0):
    if evidence_type not in {"synthetic","measured"} or len(points)<2:
        raise PmicValidationError("Invalid PMIC provenance or insufficient data")
    _finite(start_v,"start_v",0,10)
    _finite(target_v,"target_v",0,10)
    if target_v<=start_v:
        raise PmicValidationError("target_v must exceed start_v")
    if points[0].vstore_v>start_v:
        cold_start_s=None
        cold_start_state="not_observed_initially_discharged"
    else:
        crossing=next((p for p in points if p.vstore_v>=target_v),None)
        cold_start_s=None if crossing is None else crossing.elapsed_s-points[0].elapsed_s
        cold_start_state="reached_target" if crossing else "target_not_reached"
    # Held-power electrical integration: endpoint-aligned input and output
    # energy; not PMIC efficiency while reservoir energy changes.
    ein=sum(p.input_power_w*(q.elapsed_s-p.elapsed_s) for p,q in zip(points,points[1:]))
    eout=sum(p.output_power_w*(q.elapsed_s-p.elapsed_s) for p,q in zip(points,points[1:]))
    return {
        "evidence_type":evidence_type,
        "samples":len(points),
        "observed_duration_s":points[-1].elapsed_s-points[0].elapsed_s,
        "input_electrical_energy_j":ein,
        "output_electrical_energy_j":eout,
        "initial_store_voltage_v":points[0].vstore_v,
        "final_store_voltage_v":points[-1].vstore_v,
        "cold_start_state":cold_start_state,
        "time_to_store_target_s":cold_start_s,
        "warning":"Sequential meter queries, not simultaneous; output/input ratio is NOT PMIC efficiency while VSTORE changes; no instrument calibration or device connection is independently verified.",
    }


def capture_scpi(instruments,*,steps:int,interval_s:float,monotonic=time.monotonic,sleep=time.sleep):
    """Five DMMs, one measurement per channel per sample; no source control."""
    if not isinstance(steps,int) or isinstance(steps,bool) or not 2<=steps<=10000:
        raise PmicValidationError("Expected 2..10000 samples")
    _finite(interval_s,"interval_s",0.1,3600)
    names=("vin_v","iin_a","vout_v","iout_a","vstore_v")
    commands=("MEAS:VOLT:DC?","MEAS:CURR:DC?","MEAS:VOLT:DC?","MEAS:CURR:DC?","MEAS:VOLT:DC?")
    limits=(15,10,10,10,10)
    if len(instruments)!=5:
        raise PmicValidationError("Five independent instrument channels required")
    started=monotonic()
    result=[]
    for i in range(steps):
        vals={}
        timestamp=monotonic()-started
        for meter,name,cmd,lim in zip(instruments,names,commands,limits):
            vals[name]=_finite(meter.query(cmd),name,0,lim)
        vals["elapsed_s"]=timestamp
        vals["evidence_type"]="measured"
        result.append(vals)
        if i+1<steps:
            sleep(interval_s)
    return result


def save_csv_exclusive(path:Path,rows):
    if not rows:
        raise PmicValidationError("No acquired rows")
    with path.open("x",encoding="utf-8",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    p=argparse.ArgumentParser(description="Thermo-IoT real SCPI PMIC profile / CSV analyzer")
    p.add_argument("--file",type=Path,help="Analyze existing PMIC CSV")
    p.add_argument("--meter-vin")
    p.add_argument("--meter-iin")
    p.add_argument("--meter-vout")
    p.add_argument("--meter-iout")
    p.add_argument("--meter-vstore")
    p.add_argument("--output",type=Path)
    p.add_argument("--steps",type=int,default=30)
    p.add_argument("--interval-s",type=float,default=1.0)
    args=p.parse_args(argv)
    try:
        if args.file:
            if any((args.meter_vin,args.meter_iin,args.meter_vout,args.meter_iout,args.meter_vstore,args.output)):
                raise PmicValidationError("Use --file without acquisition arguments")
            source,points=read_pmic_csv(args.file)
        else:
            ids=[args.meter_vin,args.meter_iin,args.meter_vout,args.meter_iout,args.meter_vstore]
            if not args.output or not all(ids) or len(set(ids))!=5:
                raise PmicValidationError("Supply five distinct VISA meters and a NEW --output")
            if args.output.exists():
                raise FileExistsError("Output CSV already exists")
            try:
                import pyvisa
            except ImportError as exc:
                raise PmicValidationError("Install pyvisa and a VISA backend") from exc
            with pyvisa.ResourceManager("@py") as resources:
                from contextlib import ExitStack
                with ExitStack() as stack:
                    meters=[stack.enter_context(resources.open_resource(name)) for name in ids]
                    rows=capture_scpi(meters,steps=args.steps,interval_s=args.interval_s)
            save_csv_exclusive(args.output,rows)
            source,points=read_pmic_csv(args.output)
        print(json.dumps(analyze_pmic(points,source),indent=2))
        return 0
    except (OSError,ValueError,PmicValidationError) as exc:
        print(f"PMIC bench: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
