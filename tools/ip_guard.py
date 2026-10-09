"""Pre-publication gate for confidential designs, grant files and credentials.

Designed to run locally BEFORE committing and BEFORE pushing. A successful
check does not establish patentability, confidentiality or secret-free output.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ZERO_SHA = "0" * 40
MAX_SCAN_BYTES = 5_000_000
PROTECTED_DIRS = {
    "private", "confidential", "internal", "unfiled", "patent_drafts",
    "invention_records", "trade_secrets", "unpublished", "ip_private",
}
PROTECTED_FILES = {
    "se-identity.h", "ttn-actual-uplink.json", ".env", "id_rsa",
    "id_ed25519", "appkey.txt", "lorawan_keys.json",
}
PROTECTED_SUFFIXES = (".pem", ".p12", ".pfx", ".key", ".kdbx")
MARKER = re.compile(
    rb"(?i)(?<![A-Za-z0-9_])(?:UNFILED[_-]INVENTION|DO[_-]NOT[_-]PUBLISH|"
    rb"CONFIDENTIAL[_-]INVENTION|PATENT[_-]DRAFT[_-]NONPUBLIC)(?![A-Za-z0-9_])"
)
CREDENTIAL = re.compile(
    rb"(?i)(?:-----BEGIN (?:[A-Z ]* )?PRIVATE KEY-----|"
    rb"\b(?:APP_KEY|APPKEY|LORAWAN_APPKEY|TTN_API_KEY|"
    rb"THERMO_IOT_WEBHOOK_TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{24,})"
)


def inspect_candidate(path: str, content: bytes) -> list[str]:
    """Return code-only findings; never log document bodies or private values."""
    normalized = path.replace("\\", "/").casefold()
    parts = PurePosixPath(normalized).parts
    reasons = []
    if (
        any(part in PROTECTED_DIRS for part in parts[:-1])
        or (len(parts) >= 2 and parts[-2:] in [
            ("evidence", "private"), ("data", "raw_measurements")
        ])
        or (parts and parts[-1] in PROTECTED_FILES)
        or (parts and parts[-1].endswith(PROTECTED_SUFFIXES))
        or any(p in {"raw_measurements", "private_evidence"} for p in parts[:-1])
    ):
        reasons.append("protected_path")
    if len(content) > MAX_SCAN_BYTES:
        reasons.append("oversize_requires_manual_review")
        return reasons
    if b"\x00" in content:
        reasons.append("unscannable_binary")
        return reasons
    if MARKER.search(content):
        reasons.append("unfiled_marker")
    if CREDENTIAL.search(content):
        reasons.append("credential_pattern")
    return reasons


def _git(repo: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Git inspection failed or timed out; publication denied") from exc


def _filenames(raw: bytes) -> list[str]:
    try:
        return [name.decode("utf-8") for name in raw.split(b"\0") if name]
    except UnicodeDecodeError as exc:
        raise RuntimeError("Filename cannot be decoded as UTF-8") from exc


def _safe_ref(value: str) -> str:
    if not re.fullmatch(r"[a-fA-F0-9]{40}", value):
        raise ValueError("Commit identifiers must be full 40-character hex SHA-1")
    return value


def _probe(repo: Path, path: str, spec: str) -> list[str]:
    # git show spec:path with no shell; paths are returned by Git itself.
    blob = _git(repo, "show", f"{spec}:{path}")
    return [f"{path}: {reason}" for reason in inspect_candidate(path, blob)]


def scan_staged(repo: Path) -> list[str]:
    """Use Git index blobs, not unstaged working-tree data."""
    paths = _filenames(_git(repo, "diff", "--cached", "--name-only",
                            "--diff-filter=ACMR", "-z"))
    violations = []
    for path in paths:
        violations.extend(_probe(repo, path, ""))
    return violations


def scan_git_range(repo: Path, base: str, head: str) -> list[str]:
    """Inspect EVERY new commit, including files later deleted before HEAD.

    Important: a push makes all intermediate commit objects public, not just
    the final worktree snapshot. An empty remote SHA means a new branch.
    """
    base = _safe_ref(base)
    head = _safe_ref(head)
    if base == head:
        return []
    if base != ZERO_SHA:
        # Check ancestry. Non-fast-forward updates require a human history review.
        _git(repo, "merge-base", "--is-ancestor", base, head)
        interval = f"{base}..{head}"
    else:
        interval = head
    commits = _git(repo, "rev-list", "--reverse", interval).decode("ascii").splitlines()
    violations = []
    for commit in commits:
        sha = _safe_ref(commit)
        paths = _filenames(_git(repo, "diff-tree", "--no-commit-id",
                                "--name-only", "--diff-filter=ACMR", "-z",
                                "--root", "-m", "-r", sha))
        for path in paths:
            violations.extend(_probe(repo, path, sha))
    return violations


def scan_tracked(repo: Path) -> list[str]:
    """CI hygiene on current HEAD; cannot undo disclosures already published."""
    paths = _filenames(_git(repo, "ls-tree", "-r", "--name-only", "-z", "HEAD"))
    return [msg for path in paths for msg in _probe(repo, path, "HEAD")]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Local IP disclosure and secret publication guard")
    p.add_argument("--repo", type=Path, default=Path("."))
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--staged", action="store_true")
    modes.add_argument("--tracked", action="store_true")
    modes.add_argument("--range", nargs=2, metavar=("REMOTE_SHA", "LOCAL_SHA"))
    args = p.parse_args(argv)
    try:
        if args.staged:
            hits = scan_staged(args.repo)
        elif args.tracked:
            hits = scan_tracked(args.repo)
        else:
            hits = scan_git_range(args.repo, *args.range)
    except (RuntimeError, ValueError) as exc:
        print(f"IP prepublication audit stopped: {exc}", file=sys.stderr)
        return 2
    if hits:
        print("BLOCKED: Sensitive material may be published.", file=sys.stderr)
        for hit in hits[:30]:
            print(f"  {hit}", file=sys.stderr)
        if len(hits) > 30:
            print(f"  (+{len(hits) - 30} more findings)", file=sys.stderr)
        print("Do not publish. Keep details local/private and obtain human IP review.", file=sys.stderr)
        return 1
    print("No rule matches. This is NOT patent clearance or confidentiality certification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
