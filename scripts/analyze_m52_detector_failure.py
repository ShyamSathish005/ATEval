"""Run leakage-safe diagnostics for the frozen M5.1 stylometric signal.

The script consumes externally generated M5.1 split manifests and writes new
M5.2 outputs only. Validation selects directions and thresholds; test data is
used once for frozen comparisons and is never used for selection.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ateval.detection import DetectionRecord, calculate_classification_metrics  # noqa: E402
from ateval.detectors import evaluate_stylometric_baseline  # noqa: E402

FEATURES = (
    "type_token_ratio",
    "sentence_length_mean",
    "sentence_length_variation",
    "function_word_ratio",
    "punctuation_density",
    "repeated_trigram_rate",
)


def load_records(path: Path) -> list[DetectionRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [DetectionRecord.from_dict(item) for item in data["records"]]


def load_all_records(path: Path) -> list[DetectionRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [DetectionRecord.from_dict(item) for item in data["records"]]


def score_records(records: Iterable[DetectionRecord]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for record in records:
        if record.label not in {"human", "ai"}:
            continue
        result = evaluate_stylometric_baseline(record.text)
        scored.append(
            {
                "id": record.id,
                "label": record.label,
                "y": int(record.label == "ai"),
                "original_label": record.original_label,
                "generator_model": record.generator_model,
                "domain": record.domain,
                "word_count": record.word_count(),
                "question_word_count": len((record.prompt or "").split()),
                "score": float(result["signal_score"]),
                "features": result["features"],
            }
        )
    return scored


def auroc(scores: list[float], labels: list[int]) -> float:
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have identical length")
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if not positive_count or not negative_count:
        return 0.5
    ranked = sorted(zip(scores, labels), key=lambda pair: pair[0])
    positive_rank_sum = 0.0
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][0] == ranked[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        positive_rank_sum += average_rank * sum(label for _, label in ranked[index:end])
        index = end
    wins = positive_rank_sum - positive_count * (positive_count + 1) / 2
    return wins / (positive_count * negative_count)


def select_threshold(scores: list[float], labels: list[int]) -> float:
    best = (-1.0, 0.5)
    for step in range(101):
        threshold = step / 100
        metrics = calculate_classification_metrics(scores, labels, threshold)
        youden = metrics["recall"] - metrics["false_positive_rate"]
        if youden > best[0]:
            best = (youden, threshold)
    return round(best[1], 4)


def bootstrap_ci(
    scores: list[float],
    labels: list[int],
    metric: Callable[[list[float], list[int]], float],
    *,
    seed: int,
    iterations: int = 500,
) -> tuple[float, float]:
    if len(scores) < 10 or len(set(labels)) < 2:
        return (0.0, 1.0)
    rng = random.Random(seed)
    values: list[float] = []
    indices = list(range(len(scores)))
    for _ in range(iterations):
        sample = [rng.choice(indices) for _ in indices]
        sample_labels = [labels[index] for index in sample]
        if len(set(sample_labels)) < 2:
            continue
        values.append(metric([scores[index] for index in sample], sample_labels))
    if not values:
        return (0.0, 1.0)
    values.sort()
    return round(values[int(len(values) * 0.025)], 4), round(
        values[min(len(values) - 1, int(len(values) * 0.975))], 4
    )


def evaluate(
    scored: list[dict[str, Any]],
    *,
    threshold: float,
    seed: int,
) -> dict[str, Any]:
    scores = [item["score"] for item in scored]
    labels = [item["y"] for item in scored]
    classification = calculate_classification_metrics(scores, labels, threshold)
    fpr_ci = bootstrap_ci(
        scores,
        labels,
        lambda sampled_scores, sampled_labels: calculate_classification_metrics(
            sampled_scores, sampled_labels, threshold
        )["false_positive_rate"],
        seed=seed,
    )
    return {
        "n": len(scored),
        "ai": sum(labels),
        "human": len(labels) - sum(labels),
        "threshold": threshold,
        "auroc": round(auroc(scores, labels), 4),
        "auroc_ci_95": bootstrap_ci(scores, labels, auroc, seed=seed),
        "false_positive_rate_ci_95": fpr_ci,
        **classification,
        "confusion_matrix": {
            "tp": classification["tp"],
            "fp": classification["fp"],
            "tn": classification["tn"],
            "fn": classification["fn"],
        },
    }


def fit_direction_threshold(
    validation: list[dict[str, Any]], values: Callable[[dict[str, Any]], float]
) -> tuple[int, float, float, float]:
    labels = [item["y"] for item in validation]
    raw = [values(item) for item in validation]
    forward = auroc(raw, labels)
    reverse = auroc([-value for value in raw], labels)
    direction = 1 if forward >= reverse else -1
    lower = min(raw)
    span = max(raw) - lower or 1.0
    transformed = [direction * (value - lower) / span for value in raw]
    return direction, select_threshold(transformed, labels), lower, span


def apply_fitted_transform(
    item: dict[str, Any],
    values: Callable[[dict[str, Any]], float],
    direction: int,
    lower: float,
    span: float,
) -> float:
    return direction * (values(item) - lower) / span


def feature_diagnostics(
    validation: list[dict[str, Any]], test: list[dict[str, Any]], *, seed: int
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for feature in FEATURES:
        def getter(item: dict[str, Any], name: str = feature) -> float:
            return float(item["features"][name])

        direction, threshold, lower, span = fit_direction_threshold(validation, getter)
        values = [apply_fitted_transform(item, getter, direction, lower, span) for item in test]
        labels = [item["y"] for item in test]
        output[feature] = {
            "direction": "higher_is_ai" if direction == 1 else "lower_is_ai",
            "validation_threshold": threshold,
            "validation_scale": {"min": lower, "span": span},
            "test_auroc": round(auroc(values, labels), 4),
            "test_auroc_ci_95": bootstrap_ci(values, labels, auroc, seed=seed),
            "test_metrics": calculate_classification_metrics(values, labels, threshold),
        }
    return output


def subgroup_diagnostics(
    test: list[dict[str, Any]], key: Callable[[dict[str, Any]], str], *, threshold: float, seed: int
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in test:
        groups[key(item)].append(item)
    results: dict[str, Any] = {}
    for name, items in sorted(groups.items()):
        labels = {item["y"] for item in items}
        if len(labels) == 1:
            results[name] = {
                "n": len(items),
                "ai": sum(item["y"] for item in items),
                "human": len(items) - sum(item["y"] for item in items),
                "mean_signal": round(sum(item["score"] for item in items) / len(items), 4),
                "note": "single-class subgroup; AUROC and FPR are undefined",
            }
        else:
            results[name] = evaluate(items, threshold=threshold, seed=seed)
    return results


def curve_points(scores: list[float], labels: list[int]) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    roc: list[dict[str, float]] = []
    pr: list[dict[str, float]] = []
    total_positive = sum(labels)
    for threshold in sorted(set(scores), reverse=True):
        metrics = calculate_classification_metrics(scores, labels, threshold)
        tp, fp = metrics["tp"], metrics["fp"]
        roc.append({"fpr": metrics["false_positive_rate"], "tpr": metrics["recall"]})
        pr.append({"recall": metrics["recall"], "precision": tp / (tp + fp) if tp + fp else 0.0})
    return roc, pr


def write_svg(path: Path, title: str, series: list[tuple[str, list[tuple[float, float]], str]]) -> None:
    width, height, margin = 720, 480, 60
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{margin}" y="28" font-size="18">{title}</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black"/>',
    ]
    for name, points, colour in series:
        encoded = " ".join(
            f"{margin + x * (width - 2 * margin):.1f},{height - margin - y * (height - 2 * margin):.1f}"
            for x, y in points
        )
        elements.append(f'<polyline points="{encoded}" fill="none" stroke="{colour}" stroke-width="2"/>')
        elements.append(f'<text x="{width-margin-120}" y="{margin+20*len(elements)}" fill="{colour}">{name}</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def write_feature_histograms(path: Path, test: list[dict[str, Any]]) -> None:
    width, height, margin = 960, 720, 45
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<text x="45" y="25" font-size="18">M5.2 feature distributions (test)</text>',
    ]
    for index, feature in enumerate(FEATURES):
        x0 = margin + (index % 2) * 450
        y0 = 55 + (index // 2) * 215
        panel_w, panel_h = 390, 160
        human = [item["features"][feature] for item in test if item["y"] == 0]
        ai = [item["features"][feature] for item in test if item["y"] == 1]
        lower = min(human + ai)
        upper = max(human + ai)
        width_value = upper - lower or 1.0
        bins = 16
        human_counts = [0] * bins
        ai_counts = [0] * bins
        for value, counts in ((value, human_counts) for value in human):
            counts[min(bins - 1, int((value - lower) / width_value * bins))] += 1
        for value, counts in ((value, ai_counts) for value in ai):
            counts[min(bins - 1, int((value - lower) / width_value * bins))] += 1
        maximum = max(human_counts + ai_counts) or 1
        elements.append(f'<text x="{x0}" y="{y0}" font-size="14">{feature}</text>')
        elements.append(f'<line x1="{x0}" y1="{y0+panel_h}" x2="{x0+panel_w}" y2="{y0+panel_h}" stroke="black"/>')
        for bin_index in range(bins):
            bar_x = x0 + bin_index * panel_w / bins
            bar_w = panel_w / bins - 1
            human_h = human_counts[bin_index] / maximum * (panel_h - 20)
            ai_h = ai_counts[bin_index] / maximum * (panel_h - 20)
            elements.append(
                f'<rect x="{bar_x:.1f}" y="{y0+panel_h-human_h:.1f}" width="{bar_w/2:.1f}" '
                f'height="{human_h:.1f}" fill="#64748b" opacity=".7"/>'
            )
            elements.append(
                f'<rect x="{bar_x+bar_w/2:.1f}" y="{y0+panel_h-ai_h:.1f}" width="{bar_w/2:.1f}" '
                f'height="{ai_h:.1f}" fill="#dc2626" opacity=".7"/>'
            )
    elements.append('<text x="45" y="705" fill="#64748b">human</text>')
    elements.append('<text x="95" y="705" fill="#dc2626">AI</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def run(manifest_dir: Path, output_dir: Path, *, seed: int = 42) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    validation = score_records(load_records(manifest_dir / "txd22_val_manifest.json"))
    test = score_records(load_records(manifest_dir / "txd22_test_manifest.json"))
    length_matched = score_records(load_records(manifest_dir / "txd22_length_matched_test.json"))
    mixed = load_all_records(manifest_dir / "txd22_mixed_authorship_manifest.json")

    val_scores = [item["score"] for item in validation]
    val_labels = [item["y"] for item in validation]
    threshold = select_threshold(val_scores, val_labels)
    test_scores = [item["score"] for item in test]
    test_labels = [item["y"] for item in test]

    length_direction, length_threshold, length_min, length_span = fit_direction_threshold(
        validation, lambda item: item["word_count"]
    )
    question_direction, question_threshold, question_min, question_span = fit_direction_threshold(
        validation, lambda item: item["question_word_count"]
    )
    length_values = [
        apply_fitted_transform(item, lambda value: value["word_count"], length_direction, length_min, length_span)
        for item in test
    ]
    question_values = [
        apply_fitted_transform(
            item, lambda value: value["question_word_count"], question_direction, question_min, question_span
        )
        for item in test
    ]
    random_scores = list(test_scores)
    random.Random(seed).shuffle(random_scores)

    roc, pr = curve_points(test_scores, test_labels)
    report: dict[str, Any] = {
        "metadata": {
            "analysis": "M5.2 detector failure analysis",
            "seed": seed,
            "frozen_detector": "ateval.detectors.evaluate_stylometric_baseline",
            "positive_class": "ai",
            "threshold_selection": "validation-only Youden J over 0.00..1.00 in 0.01 steps",
            "test_selection": "No test-derived feature, direction, or threshold selection",
        },
        "reproduction": {
            "validation_count": len(validation),
            "test_count": len(test),
            "threshold": threshold,
            "metrics": evaluate(test, threshold=threshold, seed=seed),
            "human_fpr": {
                "count": sum(item["y"] == 0 for item in test),
                "false_positives": sum(
                    item["y"] == 0 and item["score"] >= threshold for item in test
                ),
            },
        },
        "diagnostics": {
            "existing_combined_signal": evaluate(test, threshold=threshold, seed=seed),
            "length_only": {
                "direction": length_direction,
                "validation_threshold": length_threshold,
                "validation_scale": {"min": length_min, "span": length_span},
                "test_auroc": round(auroc(length_values, test_labels), 4),
                "test_metrics": calculate_classification_metrics(length_values, test_labels, length_threshold),
            },
            "question_length_only": {
                "direction": question_direction,
                "validation_threshold": question_threshold,
                "validation_scale": {"min": question_min, "span": question_span},
                "test_auroc": round(auroc(question_values, test_labels), 4),
                "test_metrics": calculate_classification_metrics(
                    question_values, test_labels, question_threshold
                ),
            },
            "random_permutation": {
                "test_auroc": round(auroc(random_scores, test_labels), 4),
                "test_metrics": calculate_classification_metrics(random_scores, test_labels, threshold),
            },
            "threshold_comparison": {
                str(candidate): calculate_classification_metrics(test_scores, test_labels, candidate)
                for candidate in (0.25, threshold, 0.5, 0.75)
            },
            "feature_ablations": feature_diagnostics(validation, test, seed=seed),
        },
        "length_matched": evaluate(length_matched, threshold=threshold, seed=seed),
        "subgroups": {
            "generator": subgroup_diagnostics(
                test, lambda item: item["generator_model"] or "human", threshold=threshold, seed=seed
            ),
            "length_group": subgroup_diagnostics(
                test,
                lambda item: (
                    "<100" if item["word_count"] < 100
                    else "100-200" if item["word_count"] <= 200
                    else "201-300" if item["word_count"] <= 300 else ">300"
                ),
                threshold=threshold,
                seed=seed,
            ),
            "domain": subgroup_diagnostics(test, lambda item: item["domain"], threshold=threshold, seed=seed),
        },
        "mixed_authorship": {
            "count": len(mixed),
            "by_label": {
                label: {
                    "count": len(items),
                    "mean_signal": round(sum(evaluate_stylometric_baseline(item.text)["signal_score"] for item in items) / len(items), 4),
                }
                for label, items in sorted(
                    ((label, [item for item in mixed if item.original_label == label])
                     for label in {item.original_label for item in mixed}),
                    key=lambda pair: pair[0],
                )
            },
        },
        "curves": {"roc": roc, "precision_recall": pr},
        "feature_availability": {
            "implemented_and_analyzed": list(FEATURES),
            "not_implemented_in_frozen_baseline": ["MTLD", "readability", "vocabulary_distribution"],
            "not_available_in_txd22_adapter": ["human_participant_id", "discipline_subdomain", "citations", "equations"],
        },
    }
    (output_dir / "m52_failure_analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_svg(
        output_dir / "roc_curve.svg",
        "M5.2 ROC curve",
        [("stylometric baseline", [(point["fpr"], point["tpr"]) for point in roc], "#2563eb")],
    )
    write_feature_histograms(output_dir / "feature_distributions.svg", test)
    write_svg(
        output_dir / "precision_recall_curve.svg",
        "M5.2 precision-recall curve",
        [("stylometric baseline", [(point["recall"], point["precision"]) for point in pr], "#059669")],
    )
    (output_dir / "confusion_matrix.json").write_text(
        json.dumps(report["diagnostics"]["existing_combined_signal"]["confusion_matrix"], indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/milestone5_2"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = run(args.manifest_dir, args.output_dir, seed=args.seed)
    print(json.dumps(report["reproduction"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
