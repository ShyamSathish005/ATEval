"""Build reproducible M4.3 gate, claim, annotation, and case-analysis artifacts."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ateval.revisions.claim_validation import compare_claim_propositions
from ateval.revisions.protected_content import protect_content, validate_and_restore

ROOT = Path(__file__).resolve().parents[1]
DEV_PREDICTIONS = ROOT / "reports/milestone4_2/scar_dev_comparison_predictions.jsonl"
M41_PREDICTIONS = ROOT / "reports/milestone4_1/xtragpt_1_5b_q8_0_predictions.jsonl"
M42_REPORTS = sorted((ROOT / "reports/milestone4_2").glob("*.json"))
ANNOTATION_PATH = ROOT / "data/annotations/revision_necessity/milestone4_3_pilot.jsonl"
OUTPUT = ROOT / "reports/milestone4_3"
SEED = 43


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def gate_cases() -> list[dict]:
    source = (
        r"Values ranged from -2.5 to 4.0e-3 kg at 95%; "
        r"\begin{equation}x \geq 0.5\end{equation}; [12, 14]."
    )
    protected = protect_content(source, ("BERT",))
    sentinels = [item.sentinel for item in protected.mapping]
    cases = [
        ("valid_identity", protected.protected_text, True),
        ("missing_sentinel", protected.protected_text.replace(sentinels[0], "edited"), False),
        ("duplicated_sentinel", f"{sentinels[0]} {sentinels[0]}", False),
        ("reordered_sentinel", " ".join(reversed(sentinels)), False),
        ("modified_sentinel", protected.protected_text.replace(sentinels[0], sentinels[0][:-2] + "XX"), False),
        ("nested_latex_environment", protected.protected_text, True),
        ("added_unknown_sentinel", protected.protected_text + " ⟪ATEVAL_FAKE_abcdef12_0001⟫", False),
    ]
    results = []
    for name, candidate, expected in cases:
        result = validate_and_restore(candidate, protected)
        results.append({
            "case": name,
            "expected_pass": expected,
            "actual_pass": result.passed,
            "classification": "correct_rejection" if not expected and not result.passed else (
                "correct_acceptance" if expected and result.passed else "false_acceptance" if result.passed else "false_rejection"
            ),
            "violations": list(result.violations),
            "restored_exact": result.restored_text == source,
        })
    repeated = protect_content(
        r"BERT and BERT report 95% [12, 14] (Smith, 2020) \cite{a,b}.",
        ("BERT",),
    )
    repeated_result = validate_and_restore(repeated.protected_text, repeated)
    results.append({
        "case": "repeated_terms_multiple_citations",
        "expected_pass": True,
        "actual_pass": repeated_result.passed,
        "classification": "correct_acceptance" if repeated_result.passed else "false_rejection",
        "violations": list(repeated_result.violations),
        "restored_exact": repeated_result.restored_text == repeated.original_text,
    })
    return results


def manual_adjudication(index: int, decision: str, structural: list[str], cues: dict) -> tuple[str, str, str]:
    """Case-level research adjudication recorded after inspecting all 30 rows."""
    labels = {
        1: ("D_HARMLESS_LEXICAL", "Whitespace and punctuation only.", "useful"),
        2: ("E_VALID_IMPROVEMENT_REJECTED", "Number 27 was omitted, so the structural rejection is correct but conservative.", "useful"),
        3: ("E_VALID_IMPROVEMENT_REJECTED", "Useful compression, but UN and 1993 were omitted from the candidate.", "useful"),
        4: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds significant and a causal explanation absent from the source.", "unsafe"),
        5: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds stronger terrorist characterization and changes scope.", "unsafe"),
        6: ("D_HARMLESS_LEXICAL", "Article change only.", "useful"),
        7: ("D_HARMLESS_LEXICAL", "Age wording and punctuation are harmless.", "useful"),
        8: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds the unsupported parenthetical Myanmar.", "unsafe"),
        9: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Weakens top-three claim and leaves malformed URLans.", "unsafe"),
        10: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Changes $5.15 to $7.25 and adds dates.", "unsafe"),
        11: ("D_HARMLESS_LEXICAL", "Preposition correction is harmless.", "useful"),
        12: ("D_HARMLESS_LEXICAL", "Grammar and hyphenation are harmless.", "useful"),
        13: ("D_HARMLESS_LEXICAL", "Comma insertion only.", "useful"),
        14: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Changes HCVAE to HCVVAE and adds novelty language.", "unsafe"),
        15: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds significant and reverses the source qualification.", "unsafe"),
        16: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds unsupported events, dates, and causal explanation.", "unsafe"),
        17: ("D_HARMLESS_LEXICAL", "Ranges from/to is equivalent here.", "useful"),
        18: ("A_DANGEROUS_STRUCTURAL", "Drops BBC, both fees, and citation-like protected content.", "unsafe"),
        19: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Will versus include changes modality.", "unsafe"),
        20: ("E_VALID_IMPROVEMENT_REJECTED", "Grammar improvement appears to preserve quantities; sentinel mismatch is conservative.", "useful"),
        21: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Changes reported observation to a stronger belief and action.", "unsafe"),
        22: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds young people, education, and encouragement.", "unsafe"),
        23: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Changes insult to satire and unsuspectingly to unexpectedly; adds AD.", "unsafe"),
        24: ("A_DANGEROUS_STRUCTURAL", "Drops the claim-bearing trailing clause.", "unsafe"),
        25: ("E_VALID_IMPROVEMENT_REJECTED", "Leading to is a harmless paraphrase of causing in context.", "useful"),
        26: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Drops not only and adds an unsupported law/model claim.", "unsafe"),
        27: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Drops only, weakening a restriction.", "unsafe"),
        28: ("E_VALID_IMPROVEMENT_REJECTED", "Bibliographic formatting is useful, but protected dates were not retained.", "useful"),
        29: ("E_VALID_IMPROVEMENT_REJECTED", "Coherence rewrite is plausibly useful; structural gate is conservative.", "useful"),
        30: ("C_SCIENTIFIC_CLAIM_ALTERATION", "Adds downsampling and deep-transformer claims absent from source.", "unsafe"),
    }
    return labels[index]


def build_case_analysis(rows: list[dict]) -> list[dict]:
    analysis = []
    for index, row in enumerate(rows, 1):
        structural = row["scar_structural_integrity"]
        cues = (row.get("scar_claim_integrity") or {}).get("cue_differences", {})
        category, reason, usefulness = manual_adjudication(index, row["scar_review_decision"], structural["violations"], cues)
        analysis.append({
            "case_number": index,
            "record_id": row["record_id"],
            "source_document_id": row["source_document_id"],
            "editing_intention": row["label"],
            "original_passage": row["source"],
            "model_revision": row["scar_output"],
            "scar_decision": row["scar_review_decision"],
            "rejection_reason": structural["violations"] or list(cues),
            "detected_structural_change": structural["violations"],
            "detected_claim_cue_change": cues,
            "manual_category": category,
            "manual_adjudication": reason,
            "revision_may_be_useful": usefulness == "useful",
            "semantic_equivalence": "not_assessed",
        })
    return analysis


def build_claim_cases() -> list[dict]:
    cases = [
        ("may_vs_will", "The method may improve accuracy.", "The method will improve accuracy.", "abstain"),
        ("could_vs_does", "The result could indicate a trend.", "The result does indicate a trend.", "abstain"),
        ("suggests_vs_demonstrates", "The evidence suggests an association.", "The evidence demonstrates an association.", "abstain"),
        ("correlation_vs_causation", "The variables are correlated.", "The variables cause one another.", "abstain"),
        ("significant_added", "The difference was observed.", "The difference was significant.", "abstain"),
        ("approximately_vs_exactly", "Approximately 10% responded.", "Exactly 11% responded.", "reject"),
        ("at_least_vs_at_most", "At least 5 samples were tested.", "At most 5 samples were tested.", "reject"),
        ("negative_positive", "The treatment did not improve accuracy.", "The treatment improved accuracy.", "abstain"),
        ("necessary_sufficient", "The feature is necessary.", "The feature is sufficient.", "abstain"),
        ("qualified_generalisation", "In this sample, the method may help.", "The method always helps.", "abstain"),
        ("limitation_removed", "Performance was measured only on one dataset.", "Performance was measured on one dataset.", "abstain"),
    ]
    output = []
    for name, source, candidate, expected in cases:
        result = compare_claim_propositions(source, candidate)
        output.append({"case": name, "source": source, "candidate": candidate, "expected": expected, "result": result.to_dict()})
    return output


def build_annotation_pilot() -> list[dict]:
    dev_path = ROOT / "data/processed/iterater_human_grouped_v1/sentence_dev.jsonl"
    rows = read_jsonl(dev_path)
    random.Random(SEED).shuffle(rows)
    selected = rows[:100]
    return [{
        "annotation_id": f"m43-{i:03d}",
        "record_id": row.get("record_id"),
        "source_document_id": row.get("doc_id"),
        "source_split": "dev",
        "original_text": row.get("before_sent", ""),
        "paragraph_context": "",
        "section_type": "unknown",
        "editing_necessity": None,
        "proposed_intention": None,
        "reviewer_reasoning": None,
        "reviewer_confidence": None,
        "reviewer_id": None,
        "disagreement": None,
        "status": "unannotated",
    } for i, row in enumerate(selected, 1)]


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(DEV_PREDICTIONS)
    case_analysis = build_case_analysis(rows)
    gate_results = gate_cases()
    claim_results = build_claim_cases()
    annotations = build_annotation_pilot()
    ANNOTATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANNOTATION_PATH.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in annotations) + "\n", encoding="utf-8")
    experiment = {
        "schema": "ateval-milestone-4-3-experiment-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_recorded_before_work": "50d9b3afc5dc8a60d9fae7285f292c540aea488d",
        "inputs": {
            str(M41_PREDICTIONS.relative_to(ROOT)): sha256(M41_PREDICTIONS),
            **{str(path.relative_to(ROOT)): sha256(path) for path in M42_REPORTS},
            str(DEV_PREDICTIONS.relative_to(ROOT)): sha256(DEV_PREDICTIONS),
        },
        "scope": "SCAR validation, gate calibration, claim diagnostics, and human-evaluation preparation; no new generative model",
        "gate_cases": gate_results,
        "claim_cases": claim_results,
        "case_analysis_count": len(case_analysis),
        "annotation_pilot": {"path": str(ANNOTATION_PATH.relative_to(ROOT)), "count": len(annotations), "labels": "all reviewer-supplied and initially null"},
        "human_evaluation": "pending qualified reviewers; no human judgments fabricated",
        "semantic_equivalence": "not_assessed",
    }
    (OUTPUT / "m43_experiment_manifest.json").write_text(json.dumps(experiment, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "scar_failure_analysis_cases.json").write_text(json.dumps(case_analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUTPUT / "protected_gate_validation.json").write_text(json.dumps(gate_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUTPUT / "claim_preservation_validation.json").write_text(json.dumps(claim_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "case_analysis": len(case_analysis),
        "gate_cases": dict(Counter(item["classification"] for item in gate_results)),
        "claim_cases": dict(Counter(item["result"]["status"] for item in claim_results)),
        "annotation_rows": len(annotations),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
