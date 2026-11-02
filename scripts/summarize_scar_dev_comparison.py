"""Validate and summarize the immutable paired SCAR development predictions."""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_scar_dev_comparison import (  # noqa: E402
    CONTEXT_LENGTH, DOCUMENTS, INPUT, MAX_NEW_TOKENS, MODEL_FILE, MODEL_NAME,
    PREDICTIONS, REPORT, SEED, STRATA, sample_records, digest,
)
def main() -> int:
    if REPORT.exists():
        raise FileExistsError(f"Refusing to overwrite {REPORT}")
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    documents = {str(item["doc_id"]): item for item in (json.loads(line) for line in DOCUMENTS.read_text(encoding="utf-8").splitlines() if line.strip())}
    expected = sample_records(rows, documents)
    predictions = [json.loads(line) for line in PREDICTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(predictions) != 30 or [row["record_id"] for row in predictions] != [row["record_id"] for row in expected]:
        raise ValueError("Predictions do not exactly match the fixed seeded sample")
    if len({row["source_document_id"] for row in predictions}) != 30:
        raise ValueError("The paired development sample has duplicate source documents")
    if any(row.get("source_split") != "dev" for row in predictions):
        raise ValueError("Every row must come from the declared development split")
    full_latency = [float(row["full_inference"]["elapsed_seconds"]) for row in predictions]
    scar_latency = [float(row["scar_inference"]["elapsed_seconds"]) for row in predictions if row.get("scar_inference")]
    count = len(predictions)
    model_sha256 = hashlib.sha256(MODEL_FILE.read_bytes()).hexdigest()
    report = {
        "schema": "ateval-scar-dev-comparison-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "one fixed paired development run; not used for prompt tuning or human-quality claims",
        "dataset": "IteraTeR-HUMAN document-grouped dev",
        "input_path": str(INPUT.relative_to(ROOT)),
        "input_sha256": digest(INPUT),
        "document_input_path": str(DOCUMENTS.relative_to(ROOT)),
        "document_input_sha256": digest(DOCUMENTS),
        "selected_count": count,
        "selected_document_count": len({row["source_document_id"] for row in predictions}),
        "selection": {"seed": SEED, "per_label": 10, "labels": sorted(STRATA)},
        "model": {
            "tag": MODEL_NAME,
            "model_file": str(MODEL_FILE),
            "checkpoint": {"path": str(MODEL_FILE), "size_bytes": MODEL_FILE.stat().st_size, "sha256": model_sha256},
            "upstream_repository_revision": "ebbce0efe4c726fd26df88237117367216ca42c6",
            "actual_tensor_quantization": "Q8_0 (Ollama runtime; upstream filename says q4)",
            "runtime": "local Ollama loopback with automatic Apple Metal/CPU placement",
            "prompt_mode": "published XtraGPT prompt",
            "temperature": 0.1,
            "seed": 17,
            "max_new_tokens": MAX_NEW_TOKENS,
            "context_length": CONTEXT_LENGTH,
        },
        "outcomes": {
            "label_distribution": dict(Counter(row["label"] for row in predictions)),
            "full_changed_count": sum(bool(row["full_passage_changed"]) for row in predictions),
            "full_changed_rate": sum(bool(row["full_passage_changed"]) for row in predictions) / count,
            "full_protected_integrity_pass_count": sum(bool(row["full_structural_integrity"]["passed"]) for row in predictions),
            "scar_changed_count": sum(bool(row["scar_changed"]) for row in predictions),
            "scar_changed_rate": sum(bool(row["scar_changed"]) for row in predictions) / count,
            "scar_candidate_changed_semantics": "includes rejected candidates; this is not an applied edit rate",
            "scar_accepted_for_author_review_count": sum(row["scar_review_decision"] == "ACCEPT_FOR_AUTHOR_REVIEW" for row in predictions),
            "scar_decisions": dict(Counter(row["scar_review_decision"] for row in predictions)),
            "scar_structural_integrity_pass_count": sum(bool(row["scar_structural_integrity"]["passed"]) for row in predictions),
            "scar_claim_cue_mismatch_count": sum(bool(row["scar_claim_integrity"] and row["scar_claim_integrity"]["status"] == "cue_mismatch") for row in predictions),
            "full_latency_mean_seconds": statistics.mean(full_latency),
            "scar_latency_mean_seconds": statistics.mean(scar_latency),
            "full_prompt_tokens": sum(int(row["full_inference"].get("prompt_eval_count") or 0) for row in predictions),
            "scar_prompt_tokens": sum(int(row["scar_inference"].get("prompt_eval_count") or 0) for row in predictions if row.get("scar_inference")),
            "semantic_equivalence": "not_assessed",
            "human_quality_evaluation": "pending",
        },
        "predictions_path": str(PREDICTIONS.relative_to(ROOT)),
        "predictions_sha256": hashlib.sha256(PREDICTIONS.read_bytes()).hexdigest(),
        "limitations": [
            "This is a 30-example development sample, not a final test set.",
            "IteraTeR edit labels do not certify that an edit is necessary.",
            "Adjacent context was extracted from the source-side document; revised text was not used as prompt context.",
            "The paired prompts differ by sentinel protection and SCAR's explicit selected-span plan, so this compares systems, not a single isolated factor.",
            "Automatic structural and claim-cue checks do not establish semantic equivalence.",
            "No qualified human ratings are included.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
