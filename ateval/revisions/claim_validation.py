"""Conservative claim-preservation diagnostics for M4.3 experiments.

This is a secondary, proposition-oriented diagnostic. It does not establish
semantic equivalence and is intentionally allowed to abstain when a cue change
cannot be resolved from the two passages alone.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .scar import compare_claim_cues


_NUMBER = re.compile(
    r"(?<!\w)[+-]?(?:\d+(?:[.,]\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
    r"(?:\s*(?:%|‰|°C|°F|mg|kg|mm|cm|m|km|μm|µm|s|ms|Hz))?(?!\w)",
    re.I,
)
_CLAUSE = re.compile(r"[^.!?;]+")


@dataclass(frozen=True)
class ClaimComparison:
    status: str
    reason: str
    cue_differences: dict[str, dict[str, list[str]]]
    quantitative_source: tuple[str, ...]
    quantitative_candidate: tuple[str, ...]
    proposition_count_source: int
    proposition_count_candidate: int
    confidence: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _numbers(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _NUMBER.finditer(text))


def _propositions(text: str) -> list[str]:
    return [part.strip() for part in _CLAUSE.findall(text) if part.strip()]


def compare_claim_propositions(source: str, candidate: str) -> ClaimComparison:
    """Compare claim-bearing cues and quantities without pretending to prove meaning.

    Exact quantitative changes are a high-risk rejection. Lexical cue changes,
    changed clause structure, and cue additions otherwise abstain for human
    review because equivalence requires discourse and domain context.
    """
    cue_differences = compare_claim_cues(source, candidate).cue_differences
    source_numbers, candidate_numbers = _numbers(source), _numbers(candidate)
    if source_numbers != candidate_numbers:
        return ClaimComparison(
            "REJECT_QUANTITATIVE_CHANGE",
            "Quantitative expressions differ and require correction or expert review.",
            cue_differences,
            source_numbers,
            candidate_numbers,
            len(_propositions(source)),
            len(_propositions(candidate)),
            "high",
        )
    if cue_differences or len(_propositions(source)) != len(_propositions(candidate)):
        return ClaimComparison(
            "ABSTAIN_REQUIRES_HUMAN_REVIEW",
            "Cue or proposition structure changed; lexical comparison cannot resolve the claim.",
            cue_differences,
            source_numbers,
            candidate_numbers,
            len(_propositions(source)),
            len(_propositions(candidate)),
        )
    return ClaimComparison(
        "NO_DIAGNOSTIC_DIFFERENCE",
        "No quantitative or configured claim-cue difference was detected.",
        {},
        source_numbers,
        candidate_numbers,
        len(_propositions(source)),
        len(_propositions(candidate)),
    )
