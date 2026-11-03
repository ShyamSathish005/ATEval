"""Method-honest manuscript signal report with source-mapped passages."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from ..registry import DETECTORS
from ..writing.analysis import _sections, _sentences, analyze_text
from ..detectors import evaluate_passages
from .documents import DocumentBundle, map_projection_span


REPORT_WARNING = (
    "AI-writing signals are probabilistic research diagnostics and can produce false positives. "
    "No authorship conclusion is available."
)


def _section_for(start: int, sections: list[dict[str, Any]]) -> str:
    for section in sections:
        if section["start"] <= start < section["end"]:
            return str(section["title"])
    return "Unsectioned prose"


def _context(text: str, start: int, end: int) -> str:
    left = text.rfind("\n\n", 0, start)
    right = text.find("\n\n", end)
    return text[left + 2 if left >= 0 else 0:right if right >= 0 else len(text)].strip()


def _mapped_sentences(text: str) -> list[tuple[int, int, str]]:
    """Segment blank-line blocks independently so headings never merge into prose."""
    spans = []
    for block in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, re.S):
        start = block.start()
        value = block.group(0)
        for left, right, sentence in _sentences(value):
            spans.append((start + left, start + right, sentence))
    return spans


def analyze_manuscript(bundle: DocumentBundle, *, requested_config: dict[str, Any] | None = None) -> dict[str, Any]:
    projection = bundle.projection
    profile = analyze_text(projection, document_name=bundle.name, document_format=bundle.format)
    sections = _sections(projection)
    if bundle.section_markers:
        markers = sorted(bundle.section_markers, key=lambda item: int(item["start"]))
        sections = []
        if markers[0]["start"] > 0 and projection[:markers[0]["start"]].strip():
            sections.append({"title": "Document front matter", "start": 0, "end": markers[0]["start"]})
        for index, marker in enumerate(markers):
            sections.append({"title": marker["title"] or "Untitled section", "start": marker["start"], "end": markers[index + 1]["start"] if index + 1 < len(markers) else len(projection)})
    segment_rows = []
    for ordinal, (start, end, sentence) in enumerate(_mapped_sentences(projection), start=1):
        source_map = map_projection_span(bundle, start, end, sentence)
        location_key = f"{source_map.get('path', bundle.name)}:{source_map.get('start', source_map.get('paragraph', source_map.get('page', 'na')))}:{ordinal}"
        segment_id = hashlib.sha256(f"{bundle.source_sha256}:{location_key}:{sentence}".encode("utf-8")).hexdigest()[:20]
        segment_rows.append({
            "segment_id": segment_id,
            "sentence_index": ordinal,
            "projection_start": start,
            "projection_end": end,
            "section": _section_for(start, sections),
            "text": sentence,
            "context": _context(projection, start, end),
            "source_map": source_map,
            "analysis_status": "not_analyzed",
            "highlight_state": "grey",
            "method_results": [],
            "review_status": "not_reviewed",
            "signal_note": "No supported detector analyzed this passage. Absence of a signal must not be interpreted as human-written.",
        })

    methods = []
    for spec in DETECTORS:
        executable = spec.name == "stylometric-baseline"
        methods.append({
            "detector_name": spec.name,
            "detector_version": None,
            "model_revision": None,
            "tokenizer_revision": None,
            "status": "executable_unvalidated" if executable else "unavailable",
            "implementation_status": spec.status,
            "analyzed_passage_count": 0,
            "relevant_signal_count": 0,
            "raw_score": None,
            "score_direction": "not_available",
            "score_distribution": None,
            "calibration_status": "not_calibrated",
            "uncertainty": "not_estimated",
            "domain_applicability": "experimental; no labelled benchmark or calibration" if executable else "not_run; method is not implemented and tested in ATEval",
            "execution_configuration": {"device": None, "precision": None, "parameters": {}, "optional_dependencies": list(spec.optional_dependencies)},
            "methodology": spec.description,
            "known_limitations": (["Executable heuristic with no labelled benchmark or calibration; not an authorship classifier."]
                                  if executable else ["This registered method is planned, not executable; no scores or passage signals were produced."]),
        })

    baseline = evaluate_passages(segment_rows)
    baseline_method = next(method for method in methods if method["detector_name"] == "stylometric-baseline")
    baseline_method["analyzed_passage_count"] = len(baseline)
    baseline_method["relevant_signal_count"] = sum(row["method_results"][0]["signal_score"] >= 0.5 for row in baseline)
    baseline_method["calibration_status"] = "not_calibrated"
    baseline_method["uncertainty"] = "per_passage_heuristic"

    mapped_characters = sum(pointer is not None for pointer in bundle.pointers)
    coverage = round(mapped_characters / max(1, len(projection)), 4)
    writable = bundle.write_back_supported and bundle.format != "pdf"
    editable_suggestion_count = 0
    mapped_suggestions = []
    for suggestion in profile["suggestions"]:
        mapped = map_projection_span(bundle, suggestion["start"], suggestion["end"], suggestion["source"])
        mapped_suggestions.append({**suggestion, "source_map": mapped, "review_status": "not_reviewed", "suggestion_status": "suggested" if mapped.get("editable") and writable else "read_only_source"})
        editable_suggestion_count += int(bool(mapped.get("editable") and writable))

    return {
        "schema_version": "manuscript-analysis-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document": {
            "document_id": hashlib.sha256(f"{bundle.name}:{bundle.source_sha256}".encode("utf-8")).hexdigest()[:20],
            "name": bundle.name,
            "format": bundle.format,
            "root_file": bundle.root_file,
            "source_sha256": bundle.source_sha256,
            "source_file_count": len(bundle.files),
            "write_back_supported": writable,
            "extraction": bundle.extraction,
            "characters_in_prose_projection": len(projection),
            "words_in_prose_projection": profile["counts"]["words"],
            "sentence_count": len(segment_rows),
            "section_count": len(sections),
            "sections": [{"title": section["title"], "start": section["start"], "end": section["end"]} for section in sections],
        },
        "coverage": {
            "descriptive_profile_prose_coverage": coverage,
            "ai_signal_prose_coverage": 1.0 if baseline else 0.0,
            "ai_signal_passages_analyzed": len(baseline),
            "unsupported_element_count": len(bundle.unsupported),
            "unsupported_elements": bundle.unsupported,
            "source_mapped_passage_count": sum(bool(row["source_map"].get("path") or row["source_map"].get("paragraph") is not None or row["source_map"].get("page") is not None) for row in segment_rows),
            "editable_passage_count": sum(bool(row["source_map"].get("editable")) for row in segment_rows),
        },
        "processing_configuration": {
            "execution": "local ATEval API",
            "detector_objective_used_for_editing": False,
            "requested": requested_config or {},
            "max_document_bytes": 25 * 1024 * 1024,
            "max_project_expanded_bytes": 100 * 1024 * 1024,
            "model_downloads": "disabled",
        },
        "detector_methods": methods,
        "prose_projection": projection,
        "detector_summary": {
            "available_method_count": 1,
            "unavailable_method_count": len(methods) - 1,
            "overall_authorship_probability": None,
            "interpretation": "An uncalibrated stylometric research signal is available. It is not an authorship probability and has not been validated against labelled AI and human documents.",
            "warning": REPORT_WARNING,
        },
        "descriptive_writing_profile": profile,
        "passages": baseline,
        "academic_edit_suggestions": mapped_suggestions,
        "editable_suggestion_count": editable_suggestion_count,
        "limitations": [
            REPORT_WARNING,
            "Descriptive lexical, syntax, readability, cohesion, and repetition measures are not AI detectors or evidence of authorship.",
            "No detector score is calibrated or combined into a document-level probability.",
            "Source-mapped editable passages are limited to exact contiguous source spans; passages crossing markup or DOCX runs remain read-only.",
            "DOCX tables and PDF layout are not included in editable prose in this version.",
            "PDF extraction is a read-only projection and cannot be exported as a source-preserving PDF.",
            "SCAR's automated preservation checks do not establish semantic equivalence; accepted suggestions require author review.",
        ],
    }
