"""Physical MVP dossier *documentary consistency* audit.

This tool checks hashes, basic evidence provenance, electrical CSV contracts,
a human-supplied KiCad DRC report and a matching TTN RF receipt. It cannot
establish that physical equipment was built, properly calibrated or operated
for seven uninterrupted days. Keep the entire evidence bundle private.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

from .lab import read_sweeps, analyze_sweeps
from .pmic import read_pmic_csv, analyze_pmic
from .trace import load_power_trace
from .lorawan_fieldtest import verify_recorded_attempt

REQUIRED_ARTIFACTS = {
    "teg_sweep":"teg_sweep.csv",
    "pmic_profile":"pmic_profile.csv",
    "rf_attempt":"rf_attempt.json",
    "ttn_uplink":"ttn_uplink.json",
    "active_pcb_drc":"active_pcb_drc.txt",
    "firmware_flash":"firmware_flash.log",
    "autonomous_energy_trace":"autonomous_energy_trace.csv",
}
SCHEMA = "thermo-iot-physical-evidence/v1"
MAX_FILE_BYTES = 5_000_000
MAX_MANIFEST_BYTES = 65_536


class EvidenceError(ValueError):
    pass


def _artifact(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or name.startswith(("/", "\\")):
        raise EvidenceError("Unsafe evidence filename")
    path = Path(name)
    if path.is_absolute() or any(part in ("..", ".", "") for part in path.parts):
        raise EvidenceError("Evidence cannot escape the private root")
    resolved_root = root.resolve(strict=True)
    original = root / path
    if original.is_symlink() or not original.resolve().is_relative_to(resolved_root):
        raise EvidenceError("Evidence symlink or path escape is forbidden")
    if not original.is_file():
        raise EvidenceError(f"Missing evidence artifact: {name}")
    if not 0 < original.stat().st_size <= MAX_FILE_BYTES:
        raise EvidenceError("Evidence must be nonempty and below the bounded size limit")
    return original


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(65536), b""):
            sha.update(block)
    return sha.hexdigest()


def _pairs_no_duplicates(items):
    result = {}
    for key, value in items:
        if key in result:
            raise EvidenceError("Duplicate manifest JSON key")
        result[key] = value
    return result


def _invalid_constant(item):
    raise EvidenceError("Non-finite JSON manifest field")


def _read_manifest(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise EvidenceError("Manifest missing or exceeds 64 KiB")
    try:
        with path.open(encoding="utf-8") as fp:
            obj = json.load(fp, object_pairs_hook=_pairs_no_duplicates,
                            parse_constant=_invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Invalid manifest JSON") from exc
    if not isinstance(obj, dict):
        raise EvidenceError("Manifest must be an object")
    return obj


def create_manifest(root: str|Path, output_path: str|Path) -> dict:
    """Hash existing operator-supplied files; never generate experimental data."""
    root = Path(root)
    if not root.is_dir():
        raise EvidenceError("Private evidence directory does not exist")
    entries = {}
    for label, relative in REQUIRED_ARTIFACTS.items():
        file = _artifact(root,relative)
        entries[label]={"path":relative,"sha256":_digest(file)}
    output = Path(output_path)
    # Manifest creation is separate from physical measurements and review.
    obj = {
        "schema":SCHEMA,
        "owner":"Mojeaterego - Andrzej Mikulski",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "attestation":"hash_manifest_only_unverified_physical_origin",
        "artifacts":entries,
    }
    with output.open("x",encoding="utf-8") as fp:
        json.dump(obj,fp,ensure_ascii=False,indent=2,allow_nan=False)
        fp.write("\n")
    return obj


def _read_drc(file: Path) -> None:
    text = file.read_text(encoding="utf-8", errors="replace")
    violations = re.findall(r"\*\* Found (\d+) DRC violations \*\*",text)
    unconnected = re.findall(r"\*\* Found (\d+) unconnected (?:pads|items) \*\*",text)
    if violations != ["0"] or unconnected != ["0"]:
        raise EvidenceError("Active PCB DRC report does not show exactly zero violations and zero unconnected pads")


def audit_bundle(root: str|Path, manifest_path: str|Path) -> dict:
    """Require document consistency; never issue a physical deployment approval."""
    root = Path(root)
    document = _read_manifest(Path(manifest_path))
    if document.get("schema") != SCHEMA:
        raise EvidenceError("Unknown evidence dossier schema")
    if document.get("attestation") != "hash_manifest_only_unverified_physical_origin":
        raise EvidenceError("Manifest provenance statement changed")
    entries = document.get("artifacts")
    if not isinstance(entries, dict) or set(entries) != set(REQUIRED_ARTIFACTS):
        raise EvidenceError("Incomplete physical MVP dossier")
    locations = {}
    used_paths = set()
    for name, expected in REQUIRED_ARTIFACTS.items():
        entry = entries[name]
        if not isinstance(entry, dict) or set(entry) != {"path","sha256"}:
            raise EvidenceError(f"Malformed manifest item {name}")
        relative=entry["path"]
        hexdigest=entry["sha256"]
        if not isinstance(relative,str) or relative != expected:
            raise EvidenceError("Evidence name/path does not match controlled bundle layout")
        if relative in used_paths:
            raise EvidenceError("Same evidence file assigned twice")
        used_paths.add(relative)
        if not isinstance(hexdigest,str) or not re.fullmatch(r"[a-f0-9]{64}",hexdigest):
            raise EvidenceError("Malformed SHA-256 digest")
        source=_artifact(root,relative)
        if _digest(source) != hexdigest:
            raise EvidenceError("Evidence SHA-256 digest mismatch")
        locations[name]=source

    try:
        teg=analyze_sweeps(read_sweeps(locations["teg_sweep"]))
        if teg.evidence_type != "measured":
            raise EvidenceError("TEG evidence must originate from operator-marked measurements")
        pmic_origin,pmic_points=read_pmic_csv(locations["pmic_profile"])
        if pmic_origin != "measured":
            raise EvidenceError("PMIC evidence must be operator-marked measured, not synthetic")
        pmic=analyze_pmic(pmic_points,pmic_origin)
        if pmic["cold_start_state"]!="reached_target":
            raise EvidenceError("PMIC cold-start target is not observed in CSV")
        receipt=verify_recorded_attempt(locations["rf_attempt"],locations["ttn_uplink"])
        _read_drc(locations["active_pcb_drc"])
        trace=load_power_trace(locations["autonomous_energy_trace"])
        if trace.evidence_type!="measured" or trace.points[-1].elapsed_s<604800:
            raise EvidenceError("Seven-day, operator-marked electrical energy trace not present")
        # Two endpoint readings do NOT demonstrate observation during a week.
        # Require at least hourly sampling and a bounded time gap. This
        # verifies CSV coverage only, not logger power source or calibration.
        maximum_gap=max(
            current.elapsed_s - previous.elapsed_s
            for previous,current in zip(trace.points, trace.points[1:])
        )
        if maximum_gap>3600:
            raise EvidenceError("Seven-day energy sampling gap exceeds one hour")
        if len(trace.points)<169:
            raise EvidenceError("Seven-day energy sampling coverage is insufficient")
    except (OSError, ValueError, UnicodeError) as exc:
        if isinstance(exc,EvidenceError):
            raise
        raise EvidenceError(f"Evidence content failed validation: {type(exc).__name__}") from exc

    return {
        "schema":"thermo-iot-physical-mvp-documentary-audit/v1",
        "owner":"Mojeaterego - Andrzej Mikulski",
        "file_integrity":"matches_manifest",
        "verification_level":"documentary_consistency_only",
        "teg_evidence_type":teg.evidence_type,
        "pmic_cold_start_observation":pmic["cold_start_state"],
        "radio_receipt_content":receipt["delivery_state"],
        "active_pcb_drc_reported":"zero_violations_and_zero_unconnected",
        "energy_trace_duration_s":trace.points[-1].elapsed_s,
        "energy_trace_samples":len(trace.points),
        "energy_trace_max_gap_s":maximum_gap,
        "energy_trace_coverage":"hourly_or_better_observed_timestamps_only",
        "physically_validated":False,
        "requires_independent_hardware_signoff":True,
        "not_verified":[
            "Authenticity of external LoRaWAN receipt or synchronized clock",
            "Identity, origin, calibration and uncertainty of physical instruments",
            "PCB manufacture, assembly and qualified electronics bring-up",
            "SWD flashing, MCU hardware operation and duty-cycle compliance",
            "Uninterrupted autonomous TEG-powered seven-day operation",
            "Patentability, ownership chain or freedom-to-operate",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline confidential Thermo-IoT physical MVP evidence integrity audit")
    parser.add_argument("--root",type=Path,required=True,help="Private local directory (never commit raw evidence)")
    parser.add_argument("--manifest",type=Path,help="Manifest path, default private root/manifest.json")
    parser.add_argument("--create-manifest",action="store_true",
                        help="Make hash index of existing files; never creates physical measurements")
    args = parser.parse_args(argv)
    manifest=args.manifest or args.root/"manifest.json"
    try:
        if args.create_manifest:
            report=create_manifest(args.root,manifest)
        else:
            report=audit_bundle(args.root,manifest)
    except (OSError,EvidenceError) as exc:
        print(f"Private MVP evidence audit FAILED: {exc}",file=sys.stderr)
        return 2
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
