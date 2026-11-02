"""Revision-stage statistics without a quality-improvement assumption."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from .schema import RevisionRecord


def analyze_revision_depth(records: Iterable[RevisionRecord]) -> dict[str, Any]:
    grouped: dict[str, list[RevisionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.source_document_id].append(record)
    stages: dict[str, dict[str, float]] = defaultdict(lambda: {"records": 0, "changed_chars": 0, "total_chars": 0})
    for group in grouped.values():
        for record in group:
            stage = str(record.revision_stage if record.revision_stage is not None else "unknown")
            entry = stages[stage]
            entry["records"] += 1
            entry["changed_chars"] += sum((span.before_end or 0) - (span.before_start or 0) + (span.after_end or 0) - (span.after_start or 0) for span in record.edit_spans)
            entry["total_chars"] += len(record.original_text) + len(record.revised_text)
    report = {}
    for stage, values in sorted(stages.items(), key=lambda item: (item[0] == "unknown", item[0])):
        report[stage] = {"records": int(values["records"]), "changed_character_ratio_proxy": values["changed_chars"] / values["total_chars"] if values["total_chars"] else 0.0}
    return {"source_document_count": len(grouped), "stages": report, "quality_direction_assumed": False, "note": "Revision stage is a process index, not a quality ranking."}
