"""Selective Constraint-Aware Revision (SCAR) research prototype.

SCAR is a fail-closed orchestration baseline. The necessity gate is explicit
author control, not an unvalidated learned classifier. Protected spans are
enforced outside the generator. Semantic equivalence is never asserted.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from .academic_generation import AcademicRevisionRequest, TextGenerator, XtraGPTOllamaGenerator
from .protected_content import ProtectedText, protect_content, validate_and_restore


INTENTION_TO_DECISION = {
    "clarity": "CLARITY_IMPROVEMENT",
    "grammar": "GRAMMAR_IMPROVEMENT",
    "redundancy": "REDUNDANCY_REVIEW",
    "structure": "STRUCTURAL_IMPROVEMENT",
    "technical_review": "TECHNICAL_REVIEW_REQUIRED",
}
DECISION_TO_INTENTION = {value: key for key, value in INTENTION_TO_DECISION.items()}


@dataclass(frozen=True)
class RevisionGateResult:
    decision: str
    reason: str
    author_requested_edit: bool
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RevisionPlan:
    decision: str
    target_span: str
    target_start: int
    target_end: int
    edit_intention: str
    context: str
    constraints: tuple[str, ...]
    risk: str
    author_approval_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimIntegrityResult:
    status: str
    cue_differences: dict[str, dict[str, list[str]]]
    semantic_equivalence: str = "not_assessed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SCARRevisionResult:
    plan: RevisionPlan
    gate: RevisionGateResult
    proposed_text: str | None
    candidate_text: str | None
    review_decision: str
    structural_validation: dict[str, Any]
    claim_integrity: ClaimIntegrityResult | None
    linguistic_quality: dict[str, Any]
    inference: dict[str, Any] | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "gate": self.gate.to_dict(),
            "proposed_text": self.proposed_text,
            "candidate_text": self.candidate_text,
            "review_decision": self.review_decision,
            "structural_validation": self.structural_validation,
            "claim_integrity": self.claim_integrity.to_dict() if self.claim_integrity else None,
            "linguistic_quality": self.linguistic_quality,
            "inference": self.inference,
            "warnings": list(self.warnings),
            "semantic_equivalence": "not_assessed",
            "author_approval_required": True,
        }


def revision_necessity_gate(
    *,
    selected_text: str,
    paragraph_context: str,
    intention: str | None,
    author_requested_edit: bool,
) -> RevisionGateResult:
    """Interpretable gate: abstain unless an author supplies a target and goal."""
    if not author_requested_edit or intention == "no_edit":
        return RevisionGateResult("NO_EDIT_REQUIRED", "No edit was requested by the author.", False, None)
    if (not selected_text.strip() or not paragraph_context.strip()
            or _normalized_space(paragraph_context) == _normalized_space(selected_text)
            or intention not in INTENTION_TO_DECISION):
        return RevisionGateResult(
            "INSUFFICIENT_CONTEXT",
            "A non-empty target, surrounding paragraph, explicit editing intention, and author request are required.",
            True,
            None,
        )
    if intention == "technical_review":
        return RevisionGateResult(
            "TECHNICAL_REVIEW_REQUIRED",
            "The requested change requires a subject expert; generation is not started by this baseline.",
            True,
            None,
        )
    return RevisionGateResult(
        INTENTION_TO_DECISION[intention],
        "An author explicitly requested this selected edit intention; this is not a model-estimated probability of necessity.",
        True,
        None,
    )


def _normalized_space(text: str) -> str:
    return " ".join(text.split()).casefold()


def create_revision_plan(
    paragraph_context: str,
    *,
    target_start: int,
    target_end: int,
    intention: str | None,
    author_requested_edit: bool,
    protected_terms: tuple[str, ...] = (),
) -> tuple[RevisionGateResult, RevisionPlan]:
    if target_start < 0 or target_end < target_start or target_end > len(paragraph_context):
        raise ValueError("target offsets must identify a span inside paragraph_context")
    target = paragraph_context[target_start:target_end]
    gate = revision_necessity_gate(
        selected_text=target,
        paragraph_context=paragraph_context,
        intention=intention,
        author_requested_edit=author_requested_edit,
    )
    protected = protect_content(target, protected_terms)
    risk = "high" if protected.mapping else ("medium" if intention in {"structure", "redundancy"} else "low")
    constraints = (
        "edit only the selected span",
        "preserve all protected placeholders exactly once and in order",
        "preserve scientific claims, scope, negation, modality, causal relations, and limitations",
        "preserve all content outside the selected span",
        "make no unsupported additions or citations",
        "return the original selected span if no safe useful change is possible",
    )
    plan = RevisionPlan(
        decision=gate.decision,
        target_span=target,
        target_start=target_start,
        target_end=target_end,
        edit_intention=intention or "unspecified",
        context=paragraph_context,
        constraints=constraints,
        risk=risk,
    )
    return gate, plan


_CLAIM_CUES: dict[str, re.Pattern[str]] = {
    "negation": re.compile(r"\b(?:not|no|never|neither|nor|without|cannot|can't|doesn't|don't|isn't|wasn't|weren't|didn't)\b", re.I),
    "modality": re.compile(r"\b(?:may|might|could|can|should|would|will|must|possible|possibly|likely|unlikely|suggest|suggests|suggested|appears|appear|seems|seem)\b", re.I),
    "quantification": re.compile(r"\b(?:all|any|some|many|most|few|several|only|at least|at most|approximately|about|roughly|more than|less than|up to|between)\b", re.I),
    "causality": re.compile(r"\b(?:because|therefore|thus|hence|cause[sd]?|result(?:s|ed)? in|lead(?:s|ing)? to|due to|associated with|correlated with|related to)\b", re.I),
    "claim_strength": re.compile(r"\b(?:significant(?:ly)?|robust(?:ly)?|prove[sd]?|demonstrate[sd]?|confirm(?:s|ed)?|establish(?:es|ed)?|superior|outperform(?:s|ed)?|always|never)\b", re.I),
}


def compare_claim_cues(source: str, candidate: str) -> ClaimIntegrityResult:
    differences: dict[str, dict[str, list[str]]] = {}
    for kind, pattern in _CLAIM_CUES.items():
        before = [match.group(0).casefold() for match in pattern.finditer(source)]
        after = [match.group(0).casefold() for match in pattern.finditer(candidate)]
        if before != after:
            differences[kind] = {"source": before, "candidate": after}
    return ClaimIntegrityResult("cue_mismatch" if differences else "no_cue_mismatch_detected", differences)


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _generation_was_capped(inference: dict[str, Any] | None, max_new_tokens: int) -> bool:
    if not inference:
        return False
    finish_reason = str(inference.get("done_reason", "")).casefold()
    try:
        token_count = int(inference.get("eval_count", 0) or 0)
    except (TypeError, ValueError):
        token_count = 0
    return finish_reason in {"length", "max_tokens", "max_new_tokens"} or token_count >= max_new_tokens


def _rejected_result(
    gate: RevisionGateResult,
    plan: RevisionPlan,
    *,
    review_decision: str,
    warnings: tuple[str, ...],
    structural: dict[str, Any] | None = None,
    candidate: str | None = None,
    inference: dict[str, Any] | None = None,
    claim: ClaimIntegrityResult | None = None,
) -> SCARRevisionResult:
    return SCARRevisionResult(
        plan, gate, None, candidate, review_decision,
        structural or {"passed": False, "violations": list(warnings)}, claim,
        {"status": "not_assessed", "reason": "linguistic quality requires reviewer judgment"}, inference, warnings,
    )


class SCARRevisionEngine:
    """Run the author gate, minimal-span plan, placeholder protection, then review."""

    def __init__(self, generator: TextGenerator) -> None:
        self.generator = generator

    def revise(
        self,
        paragraph_context: str,
        *,
        target_start: int,
        target_end: int,
        intention: str | None,
        author_requested_edit: bool,
        protected_terms: tuple[str, ...] = (),
        citations: tuple[str, ...] = (),
        section: str = "unknown",
    ) -> SCARRevisionResult:
        gate, plan = create_revision_plan(
            paragraph_context,
            target_start=target_start,
            target_end=target_end,
            intention=intention,
            author_requested_edit=author_requested_edit,
            protected_terms=protected_terms,
        )
        source = plan.target_span
        if gate.decision == "NO_EDIT_REQUIRED":
            return SCARRevisionResult(
                plan, gate, source, source, "NO_CHANGE", {"passed": True, "skipped": True, "reason": gate.reason},
                None, {"status": "not_assessed"}, None, (),
            )
        if gate.decision == "INSUFFICIENT_CONTEXT":
            return _rejected_result(gate, plan, review_decision="REQUIRES_EXPERT_REVIEW", warnings=(gate.reason,))
        if gate.decision == "TECHNICAL_REVIEW_REQUIRED":
            return _rejected_result(gate, plan, review_decision="REQUIRES_EXPERT_REVIEW", warnings=(gate.reason,))

        protected = protect_content(source, protected_terms)
        instruction = (
            f"Perform a minimal {intention} revision on SELECTED_CONTENT. Edit only where needed. "
            "Keep every ATEval sentinel exactly once and in its original order. Do not add claims, evidence, citations, "
            "numbers, or scientific interpretations. Return only the revised selected passage."
        )
        request = AcademicRevisionRequest(
            original_text=protected.protected_text,
            paragraph_context=paragraph_context,
            document_section=section,
            editing_instruction=instruction,
            protected_terminology=protected_terms,
            relevant_citations=citations,
        )
        if isinstance(self.generator, XtraGPTOllamaGenerator):
            raw = self.generator.generate_raw(request)
            inference = self.generator.telemetry[-1] if self.generator.telemetry else None
        else:
            proposal = self.generator.generate(request)
            raw = proposal.proposed_text
            inference = None
        validated = validate_and_restore(raw, protected)
        structural = validated.to_dict()
        if not validated.passed:
            return _rejected_result(
                gate, plan, review_decision="REJECT_STRUCTURAL_CHANGE",
                warnings=validated.violations, structural=structural, candidate=raw, inference=inference,
            )
        assert validated.restored_text is not None
        if _generation_was_capped(inference, getattr(self.generator, "max_new_tokens", 10**9)):
            return _rejected_result(
                gate, plan, review_decision="REJECT_STRUCTURAL_CHANGE",
                warnings=("generation_token_cap_reached",), structural={**structural, "passed": False, "violations": ["generation_token_cap_reached"]},
                candidate=raw, inference=inference,
            )
        if _normalized(source) == _normalized(validated.restored_text):
            return SCARRevisionResult(
                plan, gate, source, validated.restored_text, "NO_CHANGE", structural, compare_claim_cues(source, validated.restored_text),
                {"status": "not_assessed"}, inference, (),
            )
        claim = compare_claim_cues(source, validated.restored_text)
        if claim.status == "cue_mismatch":
            return _rejected_result(
                gate, plan, review_decision="REJECT_POTENTIAL_MEANING_CHANGE",
                warnings=("meaning-sensitive claim cues changed; expert review is required",), structural=structural,
                candidate=validated.restored_text, inference=inference, claim=claim,
            )
        return SCARRevisionResult(
            plan, gate, validated.restored_text, validated.restored_text, "ACCEPT_FOR_AUTHOR_REVIEW", structural, claim,
            {"status": "not_assessed", "reason": "grammar, clarity, and coherence require human evaluation"}, inference,
            ("Automated checks do not establish semantic equivalence.",),
        )
