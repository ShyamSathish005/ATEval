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
    "DATASETS_AND_LICENSING.md",
    "EVALUATION.md",
    "RESEARCH.md",
    "ROADMAP.md",
    "algorithm_implementation_matrix.md",
    "architecture.md",
    "ci_failure_root_cause.md",
    "claim_preservation_validation.md",
    "cors_upload_failure_analysis.md",
    "dataset_ingestion_report.md",
    "dataset_quality_report.md",
    "docker_runtime_report.md",
    "edit_intention_taxonomy.md",
    "extended_revision_research.md",
    "final_license_provenance_review.md",
    "human_evaluation_protocol.md",
    "human_writing_research.md",
    "implementation_audit.md",
    "installation.md",
    "intent_model_failure_analysis.md",
    "known_limitations.md",
    "literature_review.md",
    "m0_2_release_readiness.md",
    "milestone_3_initial_audit.md",
    "milestone_3_report.md",
    "milestone_4_1_failure_analysis.md",
    "milestone_4_1_generation_benchmark.md",
    "milestone_4_1_model_feasibility.md",
    "milestone_4_1_semantic_preservation.md",
    "milestone_4_2_experiment_report.md",
    "milestone_4_2_failure_taxonomy.md",
    "milestone_4_3_results.md",
    "milestone_4_3_scar_failure_analysis.md",
    "milestone_4_4_annotation_report.md",
    "milestone_4_4_human_evaluation_protocol.md",
    "milestone_4_4_results.md",
    "milestone_4_4_statistical_analysis.md",
    "milestone_4_5_implementation_audit.md",
    "milestone_4_5_report.md",
    "milestone_4_report.md",
    "no_edit_annotation_protocol.md",
    "os_installation.md",
    "protected_content_architecture.md",
    "public_demo_deployment.md",
    "python_compatibility_report.md",
    "quick_start.md",
    "release_checklist.md",
    "release_exclusion_manifest.yaml",
    "release_notes_v0.1.0-alpha.md",
    "release_readiness_report.md",
    "repository_migration_report.md",
    "research_methodology.md",
    "revision_benchmark_report.md",
    "revision_dataset_analysis.md",
    "revision_experiment_protocol.md",
    "revision_model_architecture.md",
    "scar_algorithm_specification.md",
    "scar_reviewer_handbook.md",
    "semantic_preservation_methodology.md",
    "troubleshooting.md",
    "upload_integration_test_report.md",
    "writing_engine_evaluation.md",
}
SAFE_DOCS_ASSETS = {
    "ateval-hero.svg",
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
        if remaining:
            if len(remaining) == 1 and remaining[0] in SAFE_DOCS:
                pass
            elif len(remaining) == 1 and remaining[0] == "assets":
                pass
            elif len(remaining) == 2 and remaining[0] == "assets" and remaining[1] in SAFE_DOCS_ASSETS:
                pass
            else:
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
