"""Formal definition and isolation of ATEval detection benchmark tasks.

Task A: Human versus AI text (binary, strictly excludes mixed authorship)
Task B: Mixed authorship (hybrid writing, collaborative editing, multi-turn refinement)
Task C: Academic-domain generalisation (in-domain academic vs cross-domain)
Task D: Passage-level localisation (span-level precision/recall; requires genuine span truth)
"""

from __future__ import annotations

import logging
from typing import Sequence

from .schema import AuthorshipClass, DetectionRecord, TaskKind

LOG = logging.getLogger("ateval.detection.tasks")


class TaskDefinitionError(ValueError):
    """Raised when an evaluation violates benchmark task boundaries."""


def prepare_task_a_cohort(records: Sequence[DetectionRecord]) -> list[DetectionRecord]:
    """Extract strictly binary human-vs-AI samples.
    
    Mixed-authorship samples are explicitly excluded from Task A to prevent
    forcing hybrid texts into binary classes.
    """
    cohort = []
    excluded_mixed = 0
    for record in records:
        if record.label == AuthorshipClass.MIXED.value:
            excluded_mixed += 1
            continue
        if record.label in {AuthorshipClass.HUMAN.value, AuthorshipClass.AI.value}:
            cohort.append(record)
    if excluded_mixed > 0:
        LOG.info(
            "Task A cohort: excluded %d mixed-authorship records to preserve binary task integrity.",
            excluded_mixed,
        )
    return cohort


def prepare_task_b_cohort(
    records: Sequence[DetectionRecord],
    *,
    include_controls: bool = True,
) -> list[DetectionRecord]:
    """Extract mixed-authorship evaluation samples.
    
    If include_controls is True, includes pure human and pure AI records as
    negative/positive anchors for 3-way or boundary detection tasks.
    """
    cohort = []
    for record in records:
        if record.label == AuthorshipClass.MIXED.value:
            cohort.append(record)
        elif include_controls and record.label in {AuthorshipClass.HUMAN.value, AuthorshipClass.AI.value}:
            cohort.append(record)
    return cohort


def prepare_task_c_domain_cohort(
    records: Sequence[DetectionRecord],
    *,
    target_domain: str = "academic",
) -> tuple[list[DetectionRecord], list[DetectionRecord]]:
    """Separate in-domain academic samples from out-of-domain samples.
    
    Returns (in_domain_records, out_of_domain_records).
    """
    in_domain = []
    out_of_domain = []
    target = target_domain.casefold()

    for record in records:
        rec_domain = (record.domain or "").casefold()
        if target in rec_domain:
            in_domain.append(record)
        else:
            out_of_domain.append(record)

    return in_domain, out_of_domain


def prepare_task_d_passage_cohort(
    records: Sequence[DetectionRecord],
) -> list[DetectionRecord]:
    """Extract samples for passage-level span localisation.
    
    STRICT REQUIREMENT: Only samples with verified ground-truth span annotations
    (`has_span_labels == True` and non-empty `spans`) are admitted.
    
    Raises TaskDefinitionError if called with records lacking span ground truth,
    preventing document-level labels from masquerading as passage-level ground truth.
    """
    eligible = [r for r in records if r.has_span_labels and r.spans]
    ineligible = len(records) - len(eligible)

    if not eligible:
        raise TaskDefinitionError(
            "Task D (Passage-level Localisation) requires verified span-level ground truth. "
            f"All {len(records)} provided records lack passage annotations. "
            "Converting document-level labels into passage or sentence labels is strictly prohibited."
        )

    if ineligible > 0:
        LOG.warning(
            "Task D cohort: omitted %d records lacking passage-level span annotations.",
            ineligible,
        )

    return eligible

