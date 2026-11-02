#!/usr/bin/env python3
"""Read-only failure analysis for the immutable M4.1 prediction JSONL."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ateval.revisions.generation_baselines import CITATION, NUMBER
from ateval.writing.semantic import validate_preservation

LEGACY_CITATION = re.compile(r"\[(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?(?:,\s*(?:19|20)\d{2}[a-z]?)?)(?:;\s*[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?(?:,\s*(?:19|20)\d{2}[a-z]?)?)*\]|\((?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?)(?:;\s*[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?)*\)")


def _seq(pattern, text: str) -> list[str]:
    return [match.group(0) for match in pattern.finditer(text)]


def analyze(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("prediction file contains no records")
    ids = [row["record_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("prediction file contains duplicate record IDs")
    no_op = [row for row in rows if " ".join(row["source"].casefold().split()) == " ".join(row["reference"].casefold().split())]
    changed = [row for row in rows if " ".join(row["source"].casefold().split()) != " ".join(row["output"].casefold().split())]
    numeric_failures = []
    citation_failures = []
    legacy_citation_failures = []
    citation_detector_false_positives = []
    protected_failures = []
    free_text_parser_warning = 0
    max_token_rows = []
    section_stats: dict[str, Counter[str]] = {}
    telemetry: list[dict[str, Any]] = []
    for row in rows:
        source, output = row["source"], row["output"]
        source_numbers, output_numbers = _seq(NUMBER, source), _seq(NUMBER, output)
        source_citations, output_citations = _seq(CITATION, source), _seq(CITATION, output)
        legacy_source_citations, legacy_output_citations = _seq(LEGACY_CITATION, source), _seq(LEGACY_CITATION, output)
        check = validate_preservation(source, output)
        if source_numbers != output_numbers:
            numeric_failures.append({"record_id": row["record_id"], "source_values": source_numbers, "output_values": output_numbers, "source": source, "output": output})
        if source_citations != output_citations:
            citation_failures.append({"record_id": row["record_id"], "source_citations": source_citations, "output_citations": output_citations, "source": source, "output": output})
        if legacy_source_citations != legacy_output_citations:
            legacy_citation_failures.append(row["record_id"])
            if source_citations == output_citations:
                citation_detector_false_positives.append(row["record_id"])
        if not check["protected_span_sequence_preserved"]:
            protected_failures.append({"record_id": row["record_id"], **check, "source": source, "output": output})
        if any("requested JSON schema" in warning for warning in row.get("warnings", [])):
            free_text_parser_warning += 1
        info = row.get("inference") or {}
        telemetry.append(info)
        if info.get("eval_count") == 128:
            max_token_rows.append({
                "record_id": row["record_id"],
                "ends_with_sentence_punctuation": output.rstrip().endswith((".", "?", "!", ";", ":", "\"", "’", "'", ")", "]")),
                "output_suffix": output[-180:],
                "done_reason_recorded": info.get("done_reason"),
            })
        section = str(row.get("section_type") or "unknown")
        counts = section_stats.setdefault(section, Counter())
        counts["examples"] += 1
        counts["changed"] += int(row in changed)
        counts["numeric_failures"] += int(source_numbers != output_numbers)
        counts["citation_failures"] += int(source_citations != output_citations)
        counts["protected_failures"] += int(not check["protected_span_sequence_preserved"])
    timings = [float(item["elapsed_seconds"]) for item in telemetry if item.get("elapsed_seconds") is not None]
    prompt_tokens = [int(item["prompt_eval_count"]) for item in telemetry if item.get("prompt_eval_count") is not None]
    output_tokens = [int(item["eval_count"]) for item in telemetry if item.get("eval_count") is not None]
    report = {
        "schema": "ateval-milestone4-1-failure-analysis-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "predictions_path": str(path),
        "prediction_file_sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
        "rows": len(rows),
        "documents": len({row["source_document_id"] for row in rows}),
        "changed_outputs": len(changed),
        "changed_output_rate": len(changed) / len(rows),
        "reference_no_op_rows": len(no_op),
        "reference_no_op_rows_edited": sum(row in changed for row in no_op),
        "unnecessary_edit_rate_on_reference_no_ops": sum(row in changed for row in no_op) / len(no_op) if no_op else None,
        "numeric_sequence_failures": {"count": len(numeric_failures), "rate": len(numeric_failures) / len(rows), "examples": numeric_failures[:30]},
        "citation_sequence_failures": {"count": len(citation_failures), "rate": len(citation_failures) / len(rows), "examples": citation_failures[:30]},
        "citation_detector_audit": {"legacy_pattern_mismatches": len(legacy_citation_failures), "refined_pattern_mismatches": len(citation_failures), "legacy_false_positives": len(citation_detector_false_positives), "false_positive_record_ids": citation_detector_false_positives, "interpretation": "The legacy bracket pattern classified the dataset placeholder [URL] as a citation. The refined pattern requires an author-year or numeric citation form; the three [URL] rows are not citation modifications."},
        "protected_span_sequence_failures": {"count": len(protected_failures), "rate": len(protected_failures) / len(rows), "examples": protected_failures[:30]},
        "published_free_text_misreported_as_json_parse_failure": {"count": free_text_parser_warning, "rate": free_text_parser_warning / len(rows), "interpretation": "The published XtraGPT prompt returns free-form revision text. The earlier generic response parser expected an ATEval JSON object; this is an evaluator-format mismatch, not evidence that the model output itself was malformed."},
        "generation_cap": {"configured_max_new_tokens": 128, "rows_at_cap": len(max_token_rows), "finish_reason_recorded": False, "examples": max_token_rows, "interpretation": "Rows that use the entire token budget are possible truncations. The earlier telemetry omitted finish_reason, so EOS exactly at the cap cannot be distinguished from length truncation retrospectively."},
        "context_window": {"configured_tokens": 2048, "max_prompt_eval_tokens": max(prompt_tokens, default=None), "max_prompt_plus_generated_tokens": max((p + o for p, o in zip(prompt_tokens, output_tokens)), default=None), "interpretation": "Prompt plus generated tokens stayed below the configured context in the recorded token counts."},
        "timing_seconds": {"mean": statistics.mean(timings) if timings else None, "median": statistics.median(timings) if timings else None, "p95": sorted(timings)[int(.95 * len(timings)) - 1] if timings else None, "total_generation_wall_seconds": sum(timings)},
        "section_distribution": {key: dict(value) for key, value in sorted(section_stats.items())},
        "quantization_comparison": {"status": "not_run", "reason": "Only one official GGUF tensor quantization was available and used; BF16 or an alternate quant was not evaluated, so effects cannot be attributed."},
        "semantic_equivalence": "not_assessed",
        "human_evaluation": "pending",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.predictions)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"numeric_sequence_failures", "citation_sequence_failures", "protected_span_sequence_failures", "generation_cap", "section_distribution"}}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
