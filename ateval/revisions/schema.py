"""Canonical, provenance-preserving revision annotation records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EditSpan:
    before_start: int | None
    before_end: int | None
    after_start: int | None
    after_end: int | None
    before: str | None
    after: str | None
    operation: str
    raw_intent: str | None = None
    canonical_intent: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class RevisionRecord:
    schema_version: str
    record_id: str
    source_dataset: str
    source_document_id: str
    revision_stage: int | str | None
    split: str | None
    original_text: str
    revised_text: str
    edit_spans: tuple[EditSpan, ...] = ()
    raw_labels: tuple[str, ...] = ()
    canonical_labels: tuple[str, ...] = ()
    context_before: str = ""
    context_after: str = ""
    section_type: str | None = None
    annotation_confidence: float | None = None
    source_license: str | None = None
    license_verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_record(record: RevisionRecord) -> list[str]:
    issues: list[str] = []
    if not record.record_id:
        issues.append("record_id is empty")
    if not record.source_document_id:
        issues.append("source_document_id is empty")
    if not record.source_dataset:
        issues.append("source_dataset is empty")
    if not isinstance(record.original_text, str) or not isinstance(record.revised_text, str):
        issues.append("original_text and revised_text must be strings")
    if record.annotation_confidence is not None and not 0 <= record.annotation_confidence <= 1:
        issues.append("annotation_confidence must be between 0 and 1")
    for index, span in enumerate(record.edit_spans):
        for start, end, text, label in (
            (span.before_start, span.before_end, record.original_text, "before"),
            (span.after_start, span.after_end, record.revised_text, "after"),
        ):
            if start is None and end is None:
                continue
            if start is None or end is None or start < 0 or end < start or end > len(text):
                issues.append(f"edit_spans[{index}] has invalid {label} offsets")
            elif getattr(span, label) is not None and text[start:end] != getattr(span, label):
                issues.append(f"edit_spans[{index}] {label} text does not match offsets")
        if span.confidence is not None and not 0 <= span.confidence <= 1:
            issues.append(f"edit_spans[{index}] confidence must be between 0 and 1")
    return issues
