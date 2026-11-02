"""One fixed, document-disjoint IteraTeR development comparison: full vs SCAR.

Uses the already prepared dev split, samples one record per source document in
three supported intention strata, and refuses to overwrite prior results.
This script records automatic checks only; it is not a human-quality study.
"""

from __future__ import annotations

import hashlib
import json
import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ateval.revisions.academic_generation import (  # noqa: E402
    AcademicRevisionRequest,
    XtraGPTOllamaGenerator,
    checkpoint_manifest,
    runtime_metadata,
)
from ateval.revisions.scar import SCARRevisionEngine  # noqa: E402
from ateval.revisions.protected_content import protect_content, validate_and_restore  # noqa: E402


INPUT = ROOT / "data/processed/iterater_human_grouped_v1/sentence_dev.jsonl"
DOCUMENTS = ROOT / "data/processed/iterater_human_grouped_v1/document_dev.jsonl"
PREDICTIONS = ROOT / "reports/milestone4_2/scar_dev_comparison_predictions.jsonl"
REPORT = ROOT / "reports/milestone4_2/scar_dev_comparison.json"
LOCK = ROOT / "reports/milestone4_2/scar_dev_comparison.lock"
MODEL_FILE = Path.home() / ".cache" / "ateval" / "models" / "XtraGPT-1.5B-q4.gguf"
MODEL_NAME = "ateval-xtragpt-1_5b-q8_0"
SEED = 17
MAX_NEW_TOKENS = 128
CONTEXT_LENGTH = 2048
STRATA = {"clarity": "clarity", "fluency": "grammar", "coherence": "structure"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_records(rows: list[dict[str, Any]], documents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    chosen: list[dict[str, Any]] = []
    used_docs: set[str] = set()
    for label in STRATA:
        candidates = [row for row in rows if row.get("labels") == label]
        rng.shuffle(candidates)
        count = 0
        for row in candidates:
            doc = str(row.get("doc_id", ""))
            if not doc or doc in used_docs:
                continue
            document = documents.get(doc, {})
            if len(document.get("sents_char_pos", [])) < 2 or not str(document.get("before_revision", "")) or str(document.get("before_revision", "")).find(str(row.get("before_sent", "")).strip()) < 0:
                continue
            chosen.append(row)
            used_docs.add(doc)
            count += 1
            if count == 10:
                break
        if count != 10:
            raise RuntimeError(f"Could not select 10 context-bearing unique documents for {label}; found {count}")
    return chosen


def _run() -> int:
    if PREDICTIONS.exists() or REPORT.exists():
        raise FileExistsError("Refusing to overwrite an existing SCAR development comparison artifact")
    if not INPUT.is_file() or not DOCUMENTS.is_file() or not MODEL_FILE.is_file():
        raise FileNotFoundError("Prepared IteraTeR dev data and the local XtraGPT GGUF are required")
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    documents = {str(item["doc_id"]): item for item in (json.loads(line) for line in DOCUMENTS.read_text(encoding="utf-8").splitlines() if line.strip())}
    chosen = sample_records(rows, documents)
    generator_full = XtraGPTOllamaGenerator(
        MODEL_NAME, model_file=MODEL_FILE, mode="published", max_new_tokens=MAX_NEW_TOKENS,
        context_length=CONTEXT_LENGTH, timeout_seconds=600,
    )
    generator_scar = XtraGPTOllamaGenerator(
        MODEL_NAME, model_file=MODEL_FILE, mode="published", max_new_tokens=MAX_NEW_TOKENS,
        context_length=CONTEXT_LENGTH, timeout_seconds=600,
    )
    scar_engine = SCARRevisionEngine(generator_scar)
    output_rows: list[dict[str, Any]] = []
    for index, row in enumerate(chosen, start=1):
        document = documents[str(row["doc_id"])]
        source_document = str(document["before_revision"])
        starts = [int(pos) for pos in document.get("sents_char_pos", [])]
        found_start = source_document.find(str(row["before_sent"]).strip())
        nearest = min(enumerate(starts), key=lambda item: abs(item[1] - found_start), default=None)
        if nearest is None or abs(nearest[1] - found_start) > 4:
            raise RuntimeError(f"Could not align source sentence to source document: {row.get('record_id')}")
        sentence_index, source_start = nearest
        source_end = starts[sentence_index + 1] if sentence_index + 1 < len(starts) else len(source_document)
        context_start = starts[max(0, sentence_index - 1)]
        context_end = starts[min(len(starts) - 1, sentence_index + 2)] if sentence_index + 2 < len(starts) else len(source_document)
        source = source_document[source_start:source_end].strip()
        context = source_document[context_start:context_end].strip()
        if context == source:
            raise RuntimeError(f"Selected record has no surrounding context: {row.get('record_id')}")
        intention = STRATA[str(row["labels"])]
        full_request = AcademicRevisionRequest(
            original_text=source,
            paragraph_context=context,
            document_section="unknown",
            editing_instruction={
                "clarity": "Improve clarity without adding claims or changing scope.",
                "fluency": "Improve grammar and fluency while preserving meaning.",
                "coherence": "Improve local cohesion while preserving the argument.",
            }[str(row["labels"])],
            iterater_intent={"clarity": "clarity", "fluency": "fluency", "coherence": "coherence"}[str(row["labels"])],
        )
        full_start = datetime.now(timezone.utc)
        full_text = generator_full.generate_raw(full_request)
        full_telemetry = generator_full.telemetry[-1]
        target_start = context.find(source)
        scar_result = scar_engine.revise(
            context,
            target_start=target_start,
            target_end=target_start + len(source),
            intention=intention,
            author_requested_edit=True,
            section="unknown",
        )
        scar_telemetry = scar_result.inference
        original_protected = protect_content(source)
        full_validation = validate_and_restore(full_text, original_protected)
        output_rows.append({
            "record_id": row.get("record_id"),
            "source_document_id": row.get("doc_id"),
            "source_split": "dev",
            "label": row.get("labels"),
            "source": source,
            "reference": row.get("after_sent", ""),
            "full_passage_output": full_text,
            "full_passage_changed": " ".join(full_text.split()) != " ".join(source.split()),
            "full_structural_integrity": full_validation.to_dict(),
            "full_inference": full_telemetry,
            "scar_output": scar_result.candidate_text,
            "scar_review_decision": scar_result.review_decision,
            "scar_changed": scar_result.candidate_text is not None and " ".join(scar_result.candidate_text.split()) != " ".join(source.split()),
            "scar_structural_integrity": scar_result.structural_validation,
            "scar_claim_integrity": scar_result.claim_integrity.to_dict() if scar_result.claim_integrity else None,
            "scar_inference": scar_telemetry,
            "target_context_characters": len(context),
        })
        print(f"[{index}/{len(chosen)}] {row.get('record_id')} full={full_telemetry.get('elapsed_seconds', 0):.2f}s scar={scar_telemetry.get('elapsed_seconds', 0) if scar_telemetry else 0:.2f}s {scar_result.review_decision}", flush=True)

    with PREDICTIONS.open("x", encoding="utf-8") as stream:
        for item in output_rows:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    latency = lambda key: [float(item[key].get("elapsed_seconds", 0)) for item in output_rows if item.get(key)]
    full_latencies = latency("full_inference")
    scar_latencies = latency("scar_inference")
    report = {
        "schema": "ateval-scar-dev-comparison-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "one fixed paired development run; not used for prompt tuning or human-quality claims",
        "dataset": "IteraTeR-HUMAN document-grouped dev",
        "input_path": str(INPUT.relative_to(ROOT)),
        "input_sha256": digest(INPUT),
        "document_input_path": str(DOCUMENTS.relative_to(ROOT)),
        "document_input_sha256": digest(DOCUMENTS),
        "selected_count": len(output_rows),
        "selected_document_count": len({item["source_document_id"] for item in output_rows}),
        "selection": {"seed": SEED, "per_label": 10, "labels": sorted(STRATA)},
        "model": {
            "tag": MODEL_NAME, "model_file": str(MODEL_FILE), "checkpoint": checkpoint_manifest(MODEL_FILE),
            "runtime": runtime_metadata(MODEL_NAME, base_url="http://127.0.0.1:11434", context_length=CONTEXT_LENGTH),
            "prompt_mode": "published", "temperature": 0.1, "seed": 17,
            "max_new_tokens": MAX_NEW_TOKENS, "context_length": CONTEXT_LENGTH,
        },
        "outcomes": {
            "full_changed_count": sum(item["full_passage_changed"] for item in output_rows),
            "full_changed_rate": sum(item["full_passage_changed"] for item in output_rows) / len(output_rows),
            "full_protected_integrity_pass_count": sum(bool(item["full_structural_integrity"]["passed"]) for item in output_rows),
            "scar_changed_count": sum(item["scar_changed"] for item in output_rows),
            "scar_changed_rate": sum(item["scar_changed"] for item in output_rows) / len(output_rows),
            "scar_decisions": dict(Counter(item["scar_review_decision"] for item in output_rows)),
            "scar_structural_integrity_pass_count": sum(bool(item["scar_structural_integrity"]["passed"]) for item in output_rows),
            "scar_claim_cue_mismatch_count": sum(bool(item["scar_claim_integrity"] and item["scar_claim_integrity"]["status"] == "cue_mismatch") for item in output_rows),
            "full_latency_mean_seconds": statistics.mean(full_latencies) if full_latencies else None,
            "scar_latency_mean_seconds": statistics.mean(scar_latencies) if scar_latencies else None,
            "full_prompt_tokens": sum(int(item["full_inference"].get("prompt_eval_count") or 0) for item in output_rows),
            "scar_prompt_tokens": sum(int(item["scar_inference"].get("prompt_eval_count") or 0) for item in output_rows if item.get("scar_inference")),
            "semantic_equivalence": "not_assessed",
            "human_quality_evaluation": "pending",
        },
        "predictions_path": str(PREDICTIONS.relative_to(ROOT)),
        "predictions_sha256": hashlib.sha256(PREDICTIONS.read_bytes()).hexdigest(),
        "limitations": [
            "The dev split is for development, not a final test set.",
            "IteraTeR edit labels do not certify that an edit is necessary.",
            "This paired 30-item sample is small and stratified across three intentions.",
            "Automatic structural and claim-cue checks do not establish semantic equivalence.",
            "No qualified human ratings are included.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)} and {PREDICTIONS.relative_to(ROOT)}", flush=True)
    return 0


def main() -> int:
    try:
        lock = LOCK.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise RuntimeError(f"A paired development run may already be active: {LOCK}") from exc
    try:
        lock.write(json.dumps({"pid": __import__("os").getpid(), "started_at": datetime.now(timezone.utc).isoformat()}))
        lock.flush()
        return _run()
    finally:
        lock.close()
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
