from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_archive import audit_archive, forbidden


class ReleaseArchiveTests(unittest.TestCase):
    def test_sensitive_workspace_paths_are_forbidden(self):
        for path in (
            "ateval/data/raw/paper.json", "ateval/.ateval/local.sqlite3",
            "ateval/experiments/milestone4_4/blind_key.json",
            "ateval/frontend/node_modules/package/LICENSE", "ateval/draft.tex",
            "ateval/checkpoint.gguf", "ateval/private.docx",
            "ateval/docs/release_audit.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(forbidden(path))

    def test_research_and_migration_reports_are_safe_to_archive(self):
        self.assertFalse(forbidden("ateval/docs/milestone_4_report.md"))
        self.assertFalse(forbidden("ateval/docs/ci_failure_root_cause.md"))
        for safe_path in (
            "ateval/docs/DATASETS_AND_LICENSING.md",
            "ateval/docs/EVALUATION.md",
            "ateval/docs/RESEARCH.md",
            "ateval/docs/ROADMAP.md",
            "ateval/docs/docker_runtime_report.md",
            "ateval/docs/release_checklist.md",
            "ateval/docs/release_readiness_report.md",
            "ateval/docs/assets/ateval-hero.svg",
        ):
            with self.subTest(path=safe_path):
                self.assertFalse(forbidden(safe_path))

    def test_archive_hygiene_passes_clean_and_reports_unsafe_members(self):
        with tempfile.TemporaryDirectory() as directory:
            clean = Path(directory) / "clean.tar.gz"
            with tarfile.open(clean, "w:gz") as archive:
                info = tarfile.TarInfo("ateval/README.md")
                info.size = 3
                archive.addfile(info, io.BytesIO(b"ATE"))
            self.assertEqual(audit_archive(str(clean)), [])

            unsafe = Path(directory) / "unsafe.tar.gz"
            with tarfile.open(unsafe, "w:gz") as archive:
                info = tarfile.TarInfo("ateval/data/raw/private.json")
                info.size = 3
                archive.addfile(info, io.BytesIO(b"bad"))
            self.assertEqual(audit_archive(str(unsafe)), ["ateval/data/raw/private.json"])


if __name__ == "__main__":
    unittest.main()
