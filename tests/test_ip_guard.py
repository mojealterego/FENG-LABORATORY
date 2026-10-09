"""Pre-publication IP guard regression tests.

The hook prevents common accidental disclosures before local git publication.
It cannot prevent uploads through a web UI, nor undo previous disclosures.
"""
import subprocess
import tempfile
from pathlib import Path
import unittest

from tools.ip_guard import inspect_candidate, scan_staged, scan_git_range

ZERO = "0" * 40


def git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return result.stdout.strip()


class IpGuardTests(unittest.TestCase):
    def test_blocks_private_draft_paths_even_if_content_is_empty(self):
        for candidate in (
            "private/claim-01.md",
            "patent_drafts/my_application.md",
            "CONFIDENTIAL/novel_coupler.kicad_sch",
            "invention_records/lab-note.md",
            "evidence/private/sensor-data.csv",
            ".env", "firmware/se-identity.h", "network/ttn-actual-uplink.json",
        ):
            with self.subTest(candidate=candidate):
                self.assertIn("protected_path", inspect_candidate(candidate, b""))

    def test_allows_public_literature_and_authorized_contact(self):
        content = (b"Copyright (c) 2026 Mojeaterego Andrzej Mikulski\n"
                   b"All rights reserved\n"
                   b"Email: mojealterego21@gmail.com\n"
                   b"Public background discussion of TEG and LoRaWAN.\n")
        self.assertEqual(inspect_candidate("docs/README.md", content), [])

    def test_blocks_unfiled_invention_and_credentials_without_leaking_values(self):
        for payload in (
            b"# UNFILED_INVENTION\nDo not disclose novel thermal coupler details",
            b"APP_KEY=00112233445566778899AABBCCDDEEFF\n",
            b"THERMO_IOT_WEBHOOK_TOKEN='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'\n",
            b"-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
        ):
            with self.subTest(payload=payload[:15]):
                findings = inspect_candidate("docs/notes.txt", payload)
                self.assertTrue(findings)
                self.assertTrue(set(findings) & {"unfiled_marker", "credential_pattern"})

    def test_blocks_unscannable_binary_source(self):
        self.assertIn("unscannable_binary", inspect_candidate("design/novel.bin", b"\x00\x02\xff"))

    def test_staged_scanner_reads_actual_index_not_working_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder)
            git(repo,"init")
            git(repo,"config","user.email","test@example.test")
            git(repo,"config","user.name","Test")
            (repo/"safe.txt").write_text("PUBLIC")
            git(repo,"add","safe.txt")
            self.assertEqual(scan_staged(repo),[])
            (repo/"safe.txt").write_text("UNFILED_INVENTION")
            self.assertEqual(scan_staged(repo),[])
            git(repo,"add","safe.txt")
            self.assertTrue(scan_staged(repo))

    def test_pre_push_scans_history_not_only_final_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder)
            git(repo,"init")
            git(repo,"config","user.email","test@example.test")
            git(repo,"config","user.name","Test")
            (repo/"README.md").write_text("public")
            git(repo,"add","README.md")
            git(repo,"commit","-m","safe base")
            baseline=git(repo,"rev-parse","HEAD")
            (repo/"private").mkdir()
            (repo/"private/claims.md").write_text("not filed")
            git(repo,"add",".")
            git(repo,"commit","-m","accidental invention upload")
            (repo/"private/claims.md").unlink()
            git(repo,"add","-A")
            git(repo,"commit","-m","remove sensitive file later")
            tip=git(repo,"rev-parse","HEAD")
            findings=scan_git_range(repo,baseline,tip)
            self.assertTrue(any("private/claims.md" in f for f in findings))
            self.assertEqual(scan_git_range(repo,tip,tip),[])

    def test_new_branch_upload_checks_entire_unpublished_history(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder)
            git(repo,"init")
            git(repo,"config","user.email","test@example.test")
            git(repo,"config","user.name","Test")
            (repo/"secret.env").write_text("APP_KEY=00112233445566778899AABBCCDDEEFF")
            git(repo,"add","secret.env")
            git(repo,"commit","-m","new orphan branch")
            tip=git(repo,"rev-parse","HEAD")
            self.assertTrue(scan_git_range(repo,ZERO,tip))


if __name__=="__main__":
    unittest.main()
