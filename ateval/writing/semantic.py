"""Deterministic preservation checks, explicitly not semantic equivalence."""

from __future__ import annotations

from typing import Any

from .latex import protected_spans


def validate_preservation(original: str, revised: str) -> dict[str, Any]:
    """Check exact protected-span sequence invariants and abstain on semantics."""
    before = [span["sha256"] for span in protected_spans(original)]
    after = [span["sha256"] for span in protected_spans(revised)]
    preserved = before == after
    return {
        "validator": "exact-protected-span-sequence-v1",
        "protected_span_sequence_preserved": preserved,
        "original_protected_span_count": len(before),
        "revised_protected_span_count": len(after),
        "semantic_equivalence": "not_assessed",
        "requires_author_review": True,
        "status": "protected_spans_preserved" if preserved else "protected_span_change_detected",
    }
