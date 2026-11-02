"""Leakage-aware classification metrics for revision-intent experiments."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from .classification import MultinomialIntentModel
from .schema import RevisionRecord


def classification_metrics(records: Iterable[RevisionRecord], model: MultinomialIntentModel) -> dict[str, Any]:
    evaluated = [record for record in records if record.canonical_labels]
    overlap = sorted(model.training_source_ids & {record.source_document_id for record in evaluated})
    if overlap:
        raise ValueError(f"Source-document leakage between training and evaluation: {overlap[:10]}")
    labels = set(record.canonical_labels[0] for record in evaluated)
    confusion: Counter[tuple[str, str]] = Counter()
    for record in evaluated:
        predicted, _ = model.predict(record.original_text, record.revised_text)
        labels.add(predicted)
        confusion[(record.canonical_labels[0], predicted)] += 1
    labels = sorted(labels)
    total = len(evaluated)
    correct = sum(count for (gold, pred), count in confusion.items() if gold == pred)
    per_class = {}
    f1s = []
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(confusion[(gold, label)] for gold in labels if gold != label)
        fn = sum(confusion[(label, pred)] for pred in labels if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
        f1s.append(f1)
    return {"count": total, "accuracy": correct / total if total else None, "macro_f1": sum(f1s) / len(f1s) if f1s else None, "per_class": per_class, "confusion": {f"{gold}→{pred}": count for (gold, pred), count in confusion.items()}, "source_document_leakage": False}


def majority_baseline(train: Iterable[RevisionRecord], test: Iterable[RevisionRecord]) -> dict[str, Any]:
    counts = Counter(record.canonical_labels[0] for record in train if record.canonical_labels)
    labeled = [record for record in test if record.canonical_labels]
    if not counts or not labeled:
        return {"count": len(labeled), "accuracy": None, "macro_f1": None}
    majority = counts.most_common(1)[0][0]
    correct = sum(record.canonical_labels[0] == majority for record in labeled)
    labels = sorted({record.canonical_labels[0] for record in labeled})
    f1s = []
    for label in labels:
        tp = sum(record.canonical_labels[0] == label == majority for record in labeled)
        fp = sum(record.canonical_labels[0] != label and majority == label for record in labeled)
        fn = sum(record.canonical_labels[0] == label and majority != label for record in labeled)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return {"count": len(labeled), "majority_label": majority, "accuracy": correct / len(labeled), "macro_f1": sum(f1s) / len(f1s)}


def fitted_majority_metrics(test: Iterable[RevisionRecord], model: MultinomialIntentModel) -> dict[str, Any]:
    """Evaluate a training majority label retained in the fitted artifact."""
    if not model.class_counts:
        raise ValueError("Intent model has no fitted training labels")
    majority = model.class_counts.most_common(1)[0][0]
    labeled = [record for record in test if record.canonical_labels]
    labels = sorted({record.canonical_labels[0] for record in labeled} | set(model.class_counts))
    correct = sum(record.canonical_labels[0] == majority for record in labeled)
    per_class = {}
    f1s = []
    for label in labels:
        tp = sum(record.canonical_labels[0] == label and majority == label for record in labeled)
        fp = sum(record.canonical_labels[0] != label and majority == label for record in labeled)
        fn = sum(record.canonical_labels[0] == label and majority != label for record in labeled)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1}
        f1s.append(f1)
    return {"count": len(labeled), "majority_label": majority, "accuracy": correct / len(labeled) if labeled else None, "macro_f1": sum(f1s) / len(f1s) if f1s else None, "per_class": per_class}
