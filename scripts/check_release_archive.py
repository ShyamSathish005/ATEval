"""Fail closed if a source archive contains workspace data or generated assets."""

from __future__ import annotations

import argparse
import fnmatch
import tarfile

FORBIDDEN_PARTS = {
    ".ateval", ".env", ".openai", "node_modules", "__pycache__", ".pytest_cache",
    "data", "models", "reports", "experiments", "dist",
}
FORBIDDEN_NAMES = {
    "blind_key.json", "reviewer_annotations.jsonl", "design-option-3.png",
}
FORBIDDEN_PATTERNS = (
    "*.env", ".env.*", "*.log", "*.sqlite", "*.sqlite3", "*.db",
    "*.pdf", "*.docx", "*.tex", "*.zip", "*.joblib", "*.pt", "*.pth",
    "*.safetensors", "*.gguf", "*.pyc", "*.tsbuildinfo",
)
SAFE_DOCS = {
    "installation.md", "quick_start.md", "os_installation.md", "troubleshooting.md",
    "architecture.md", "known_limitations.md", "research_methodology.md",
    "release_checklist.md", "release_exclusion_manifest.yaml",
    "public_demo_deployment.md", "release_notes_v0.1.0-alpha.md",
}


def forbidden(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    if any(part in FORBIDDEN_PARTS for part in parts):
        return True
    if any(part in FORBIDDEN_NAMES for part in parts):
        return True
    if "docs" in parts:
        index = parts.index("docs")
        remaining = parts[index + 1:]
        if remaining and (len(remaining) != 1 or remaining[0] not in SAFE_DOCS):
            return True
    return any(fnmatch.fnmatch(part, pattern) for part in parts for pattern in FORBIDDEN_PATTERNS)


def audit_archive(path: str) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        return [member.name for member in archive.getmembers() if forbidden(member.name)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="gzip-compressed source tar archive")
    args = parser.parse_args()
    issues = audit_archive(args.archive)
    if issues:
        print("Forbidden release archive entries:")
        for item in issues:
            print(f"- {item}")
        return 1
    print("Release archive hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
