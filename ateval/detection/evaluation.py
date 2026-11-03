"""Evaluation engine for the stylometric baseline on qualified benchmark datasets.

Implements:
- Pure-Python deterministic metrics: AUROC, AUPRC, Precision, Recall, F1, FPR, FNR.
- Bootstrap 95% confidence intervals.
- Validation-based threshold selection (never exposes test data).
- Subgroup evaluations: length bins, generator models, domains, mixed authorship.
- Feature association analysis (point-biserial correlation with labels).
- Negative-control false-positive analysis on human academic text.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Sequence

from ..detectors import evaluate_stylometric_baseline
from .schema import AuthorshipClass, DetectionRecord


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics with confidence intervals."""
    total_samples: int
    positive_count: int  # AI
    negative_count: int  # Human
    threshold_used: float
    auroc: float
    auprc: float
    precision: float
    recall: float
    f1: float
    accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    # 95% Bootstrap Confidence Intervals (lower, upper)
    ci_auroc: tuple[float, float] = (0.0, 0.0)
    ci_f1: tuple[float, float] = (0.0, 0.0)
    ci_fpr: tuple[float, float] = (0.0, 0.0)
    ci_fnr: tuple[float, float] = (0.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_auroc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Compute exact AUROC via Mann-Whitney U statistic (pure Python)."""
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have identical length")

    pos_scores = [s for s, y in zip(scores, labels) if y == 1]
    neg_scores = [s for s, y in zip(scores, labels) if y == 0]

    n_pos = len(pos_scores)
    n_neg = len(neg_scores)
    if n_pos == 0 or n_neg == 0:
        return 0.5  # Undefined single-class baseline

    # Pairwise comparison with ties counted as 0.5
    u_stat = 0.0
    for p in pos_scores:
        for n in neg_scores:
            if p > n:
                u_stat += 1.0
            elif p == n:
                u_stat += 0.5

    return round(u_stat / (n_pos * n_neg), 4)


def calculate_auprc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Compute Area Under Precision-Recall Curve (Average Precision)."""
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have identical length")

    total_pos = sum(labels)
    if total_pos == 0:
        return 0.0

    # Sort descending by score
    paired = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)
    tp = 0
    fp = 0
    precisions = []
    recalls = []

    for _, label in paired:
        if label == 1:
            tp += 1
        else:
            fp += 1
        precisions.append(tp / (tp + fp))
        recalls.append(tp / total_pos)

    # Trapezoidal approximation
    auprc = 0.0
    prev_r = 0.0
    for p, r in zip(precisions, recalls):
        auprc += p * (r - prev_r)
        prev_r = r

    return round(max(0.0, min(1.0, auprc)), 4)


def calculate_classification_metrics(
    scores: Sequence[float],
    labels: Sequence[int],
    threshold: float,
) -> dict[str, float]:
    """Compute thresholded classification metrics."""
    tp = sum(1 for s, y in zip(scores, labels) if s >= threshold and y == 1)
    fp = sum(1 for s, y in zip(scores, labels) if s >= threshold and y == 0)
    tn = sum(1 for s, y in zip(scores, labels) if s < threshold and y == 0)
    fn = sum(1 for s, y in zip(scores, labels) if s < threshold and y == 1)

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
    }


def find_optimal_threshold(
    val_scores: Sequence[float],
    val_labels: Sequence[int],
    *,
    metric: str = "youden",
    candidate_steps: int = 101,
) -> float:
    """Find the optimal decision threshold on a validation split.
    
    Metrics:
    - 'youden': Youden's J statistic (Sensitivity + Specificity - 1 = Recall - FPR)
    - 'f1': Macro or positive F1 score
    """
    best_score = -1.0
    best_thresh = 0.5

    for step in range(candidate_steps):
        thresh = step / (candidate_steps - 1)
        res = calculate_classification_metrics(val_scores, val_labels, thresh)
        if metric == "f1":
            target = res["f1"]
        elif metric == "youden":
            target = res["recall"] - res["false_positive_rate"]
        else:
            raise ValueError(f"Unknown threshold selection metric: {metric}")

        if target > best_score:
            best_score = target
            best_thresh = thresh

    return round(best_thresh, 4)


def bootstrap_ci(
    scores: Sequence[float],
    labels: Sequence[int],
    metric_fn: Callable[[list[float], list[int]], float],
    *,
    n_bootstraps: int = 500,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute empirical bootstrap confidence interval for a metric."""
    n = len(scores)
    if n < 5:
        return (0.0, 1.0)

    rng = random.Random(seed)
    indices = list(range(n))
    estimates: list[float] = []

    for _ in range(n_bootstraps):
        sampled = rng.choices(indices, k=n)
        sub_scores = [scores[i] for i in sampled]
        sub_labels = [labels[i] for i in sampled]
        # Skip if bootstrap sample contains only one class
        if len(set(sub_labels)) < 2:
            continue
        try:
            val = metric_fn(sub_scores, sub_labels)
            estimates.append(val)
        except Exception:
            continue

    if not estimates:
        return (0.0, 1.0)

    estimates.sort()
    alpha = (1.0 - ci) / 2.0
    low_idx = int(alpha * len(estimates))
    high_idx = int((1.0 - alpha) * len(estimates))
    low_idx = max(0, min(low_idx, len(estimates) - 1))
    high_idx = max(0, min(high_idx, len(estimates) - 1))

    return round(estimates[low_idx], 4), round(estimates[high_idx], 4)


def bootstrap_proportion_ci(
    events: Sequence[bool],
    *,
    n_bootstraps: int = 500,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute a percentile bootstrap interval for a binary event rate."""
    if len(events) < 5:
        return (0.0, 1.0)
    rng = random.Random(seed)
    estimates = [
        sum(rng.choice(events) for _ in events) / len(events)
        for _ in range(n_bootstraps)
    ]
    estimates.sort()
    alpha = (1.0 - ci) / 2.0
    low = max(0, min(int(alpha * len(estimates)), len(estimates) - 1))
    high = max(0, min(int((1.0 - alpha) * len(estimates)), len(estimates) - 1))
    return round(estimates[low], 4), round(estimates[high], 4)


def evaluate_records(
    records: Sequence[DetectionRecord],
    *,
    threshold: float = 0.5,
    run_bootstrap: bool = True,
    seed: int = 42,
) -> tuple[EvaluationMetrics, list[dict[str, Any]]]:
    """Run stylometric baseline on a sequence of records and calculate metrics."""
    scores: list[float] = []
    labels: list[int] = []
    detailed_outputs: list[dict[str, Any]] = []

    for rec in records:
        # Task A: binary human (0) vs AI (1). Mixed authorship records are excluded from binary labels
        if rec.label == AuthorshipClass.HUMAN.value:
            y = 0
        elif rec.label == AuthorshipClass.AI.value:
            y = 1
        else:
            # Skip mixed records from standard binary metric aggregation
            continue

        res = evaluate_stylometric_baseline(rec.text)
        signal = float(res["signal_score"])
        scores.append(signal)
        labels.append(y)

        detailed_outputs.append({
            "id": rec.id,
            "label": rec.label,
            "original_label": rec.original_label,
            "generator_model": rec.generator_model,
            "domain": rec.domain,
            "word_count": rec.word_count(),
            "signal_score": signal,
            "uncertainty": res["uncertainty"],
            "features": res["features"],
        })

    if not scores:
        raise ValueError("No eligible binary (human/ai) records found for evaluation.")

    base_metrics = calculate_classification_metrics(scores, labels, threshold)
    auroc = calculate_auroc(scores, labels)
    auprc = calculate_auprc(scores, labels)

    ci_auroc = (0.0, 0.0)
    ci_f1 = (0.0, 0.0)
    ci_fpr = (0.0, 0.0)
    ci_fnr = (0.0, 0.0)

    if run_bootstrap and len(scores) >= 10:
        ci_auroc = bootstrap_ci(scores, labels, calculate_auroc, seed=seed)
        ci_f1 = bootstrap_ci(
            scores, labels,
            lambda s, y: calculate_classification_metrics(s, y, threshold)["f1"],
            seed=seed,
        )
        ci_fpr = bootstrap_ci(
            scores, labels,
            lambda s, y: calculate_classification_metrics(s, y, threshold)["false_positive_rate"],
            seed=seed,
        )
        ci_fnr = bootstrap_ci(
            scores, labels,
            lambda s, y: calculate_classification_metrics(s, y, threshold)["false_negative_rate"],
            seed=seed,
        )

    metrics = EvaluationMetrics(
        total_samples=len(scores),
        positive_count=sum(labels),
        negative_count=len(labels) - sum(labels),
        threshold_used=threshold,
        auroc=auroc,
        auprc=auprc,
        precision=base_metrics["precision"],
        recall=base_metrics["recall"],
        f1=base_metrics["f1"],
        accuracy=base_metrics["accuracy"],
        false_positive_rate=base_metrics["false_positive_rate"],
        false_negative_rate=base_metrics["false_negative_rate"],
        ci_auroc=ci_auroc,
        ci_f1=ci_f1,
        ci_fpr=ci_fpr,
        ci_fnr=ci_fnr,
    )

    return metrics, detailed_outputs


def evaluate_by_subgroup(
    records: Sequence[DetectionRecord],
    key_fn: Callable[[DetectionRecord], str],
    *,
    threshold: float = 0.5,
) -> dict[str, dict[str, Any]]:
    """Evaluate performance partitioned by a categorical attribute."""
    subgroups: dict[str, list[DetectionRecord]] = defaultdict(list)
    for r in records:
        group_key = key_fn(r)
        if group_key:
            subgroups[group_key].append(r)

    results = {}
    for group_name, group_records in subgroups.items():
        try:
            metrics, _ = evaluate_records(group_records, threshold=threshold, run_bootstrap=False)
            results[group_name] = metrics.to_dict()
        except ValueError:
            # Single class or empty cohort
            results[group_name] = {
                "total_samples": len(group_records),
                "note": "single class cohort or insufficient binary variation",
            }

    return results


def analyze_feature_associations(
    detailed_outputs: Sequence[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Compute correlation between individual stylometric features and true labels.
    
    Calculates point-biserial correlation (Pearson r between binary label y and continuous feature x),
    mean in Human vs mean in AI, to reveal what features drive separation.
    """
    feature_names = [
        "type_token_ratio",
        "sentence_length_mean",
        "sentence_length_variation",
        "function_word_ratio",
        "punctuation_density",
        "repeated_trigram_rate",
    ]

    labels = [1 if d["label"] == AuthorshipClass.AI.value else 0 for d in detailed_outputs]
    n = len(labels)
    if n < 5 or len(set(labels)) < 2:
        return {}

    n_pos = sum(labels)
    n_neg = n - n_pos

    correlations = {}
    for feat in feature_names:
        values = [d["features"].get(feat, 0.0) for d in detailed_outputs]
        human_vals = [v for v, y in zip(values, labels) if y == 0]
        ai_vals = [v for v, y in zip(values, labels) if y == 1]

        mean_h = statistics.mean(human_vals) if human_vals else 0.0
        mean_ai = statistics.mean(ai_vals) if ai_vals else 0.0
        sd_total = statistics.pstdev(values) if len(values) > 1 else 0.0

        # Point-biserial correlation formula: r_pb = ((mean_pos - mean_neg) / sd) * sqrt(p * q)
        if sd_total > 0:
            r_pb = ((mean_ai - mean_h) / sd_total) * math.sqrt((n_pos / n) * (n_neg / n))
        else:
            r_pb = 0.0

        correlations[feat] = {
            "human_mean": round(mean_h, 4),
            "ai_mean": round(mean_ai, 4),
            "difference": round(mean_ai - mean_h, 4),
            "point_biserial_correlation": round(r_pb, 4),
        }

    return correlations


def evaluate_mixed_authorship_cohort(
    records: Sequence[DetectionRecord],
) -> dict[str, Any]:
    """Evaluate Task B: Stylometric baseline behavior on mixed-authorship text.
    
    Reports mean signal scores and distributions across mixed-authorship subtypes
    without forcing them into a binary classification metric.
    """
    mixed_records = [r for r in records if r.label == AuthorshipClass.MIXED.value]
    if not mixed_records:
        return {"total_mixed": 0, "results_by_subtype": {}}

    subtypes: dict[str, list[float]] = defaultdict(list)
    for r in mixed_records:
        res = evaluate_stylometric_baseline(r.text)
        subtypes[r.original_label].append(float(res["signal_score"]))

    summary = {}
    for subtype, scores in subtypes.items():
        summary[subtype] = {
            "count": len(scores),
            "mean_signal_score": round(statistics.mean(scores), 4),
            "min_signal_score": round(min(scores), 4),
            "max_signal_score": round(max(scores), 4),
            "stdev": round(statistics.pstdev(scores), 4) if len(scores) > 1 else 0.0,
        }

    return {
        "total_mixed": len(mixed_records),
        "results_by_subtype": summary,
        "interpretation": "Mixed-authorship samples occupy intermediate signal spaces; not binary classifiable.",
    }
