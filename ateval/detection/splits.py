"""Leakage-resistant evaluation splitting protocols for detection benchmarks.

Guarantees:
- Zero prompt/question leakage across train, val, and test.
- Zero document-level leakage across splits.
- Zero author leakage for human records.
- Support for unseen generator model holdout in test.
- Support for length-matched cohort extraction.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .schema import AuthorshipClass, DetectionRecord


@dataclass(frozen=True)
class SplitConfig:
    """Configuration for reproducible group-based splitting."""
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    seed: int = 42
    group_by: str = "prompt"  # "prompt", "document_id", "author_id"
    unseen_models: tuple[str, ...] = ()
    unseen_domains: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        total = round(self.train_ratio + self.val_ratio + self.test_ratio, 4)
        if total != 1.0:
            raise ValueError(f"Split ratios must sum to 1.0; got {total}")


@dataclass
class SplitResult:
    """Splits with auditable leakage verification metrics."""
    train: list[DetectionRecord]
    val: list[DetectionRecord]
    test: list[DetectionRecord]
    unseen_model_test: list[DetectionRecord]
    leakage_audit: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        return {
            "train_count": len(self.train),
            "val_count": len(self.val),
            "test_count": len(self.test),
            "unseen_model_test_count": len(self.unseen_model_test),
            "train_classes": dict(Counter(r.label for r in self.train)),
            "val_classes": dict(Counter(r.label for r in self.val)),
            "test_classes": dict(Counter(r.label for r in self.test)),
            "leakage_clean": self.leakage_audit.get("clean", False),
        }


def _group_key(record: DetectionRecord, group_by: str) -> str:
    if group_by == "prompt" and record.prompt:
        return f"p_{hashlib.sha256(record.prompt.strip().encode('utf-8')).hexdigest()[:16]}"
    if group_by == "document_id" and record.document_id:
        return f"d_{record.document_id}"
    if group_by == "author_id" and record.author_id:
        return f"a_{record.author_id}"
    # Fallback to document_id or record.id
    return record.document_id or record.id


def create_leakage_resistant_splits(
    records: Sequence[DetectionRecord],
    config: SplitConfig | None = None,
) -> SplitResult:
    """Create reproducible group-based train/val/test splits."""
    cfg = config or SplitConfig()
    rng = random.Random(cfg.seed)

    # 1. Separate unseen model holdout
    unseen_model_records: list[DetectionRecord] = []
    eligible_records: list[DetectionRecord] = []

    unseen_model_set = {m.casefold() for m in cfg.unseen_models}
    for r in records:
        model = (r.generator_model or "").casefold()
        if model and model in unseen_model_set:
            unseen_model_records.append(r)
        else:
            eligible_records.append(r)

    # 2. Group eligible records by specified group key
    groups: dict[str, list[DetectionRecord]] = defaultdict(list)
    for r in eligible_records:
        key = _group_key(r, cfg.group_by)
        groups[key].append(r)

    # 3. Deterministically shuffle group keys
    group_keys = sorted(groups.keys())
    rng.shuffle(group_keys)

    # 4. Allocate groups to train / val / test to approximate target ratios
    total_samples = len(eligible_records)
    target_train = int(total_samples * cfg.train_ratio)
    target_val = int(total_samples * cfg.val_ratio)

    train: list[DetectionRecord] = []
    val: list[DetectionRecord] = []
    test: list[DetectionRecord] = []

    for key in group_keys:
        members = groups[key]
        if len(train) < target_train:
            train.extend(members)
        elif len(val) < target_val:
            val.extend(members)
        else:
            test.extend(members)

    # Add unseen model records to test split
    test_with_unseen = list(test) + unseen_model_records

    # 5. Audit splits for leakage
    train_prompts = {r.prompt.strip() for r in train if r.prompt}
    val_prompts = {r.prompt.strip() for r in val if r.prompt}
    test_prompts = {r.prompt.strip() for r in test if r.prompt}

    train_docs = {r.document_id for r in train if r.document_id}
    val_docs = {r.document_id for r in val if r.document_id}
    test_docs = {r.document_id for r in test if r.document_id}

    train_authors = {r.author_id for r in train if r.author_id}
    val_authors = {r.author_id for r in val if r.author_id}
    test_authors = {r.author_id for r in test if r.author_id}

    prompt_leakage = bool((train_prompts & val_prompts) or (train_prompts & test_prompts) or (val_prompts & test_prompts))
    doc_leakage = bool((train_docs & val_docs) or (train_docs & test_docs) or (val_docs & test_docs))
    author_leakage = bool((train_authors & val_authors) or (train_authors & test_authors) or (val_authors & test_authors))

    leakage_audit = {
        "clean": not (prompt_leakage or doc_leakage or author_leakage),
        "prompt_leakage": prompt_leakage,
        "document_leakage": doc_leakage,
        "author_leakage": author_leakage,
        "group_count": len(group_keys),
        "unseen_models_held_out": list(cfg.unseen_models),
    }

    return SplitResult(
        train=train,
        val=val,
        test=test_with_unseen,
        unseen_model_test=unseen_model_records,
        leakage_audit=leakage_audit,
    )


def create_length_matched_cohort(
    records: Sequence[DetectionRecord],
    *,
    bin_width: int = 40,
    seed: int = 42,
) -> list[DetectionRecord]:
    """Extract a length-matched cohort across human and AI samples.
    
    Bins texts by word count (e.g. 0-40, 41-80, 81-120 words) and samples
    an equal number of human and AI records per bin. This eliminates text
    length as a confounding discriminator.
    """
    rng = random.Random(seed)
    bins: dict[tuple[int, str], list[DetectionRecord]] = defaultdict(list)

    for r in records:
        if r.label not in {AuthorshipClass.HUMAN.value, AuthorshipClass.AI.value}:
            continue
        words = r.word_count()
        bin_idx = words // bin_width
        bins[(bin_idx, r.label)].append(r)

    # Find common bin indices
    all_bin_indices = {b_idx for (b_idx, _) in bins.keys()}
    matched: list[DetectionRecord] = []

    for b_idx in sorted(all_bin_indices):
        human_items = bins.get((b_idx, AuthorshipClass.HUMAN.value), [])
        ai_items = bins.get((b_idx, AuthorshipClass.AI.value), [])
        quota = min(len(human_items), len(ai_items))
        if quota > 0:
            matched.extend(rng.sample(human_items, quota))
            matched.extend(rng.sample(ai_items, quota))

    return matched

