"""Evaluate the existing stylometric baseline on qualified detection benchmark splits.

Runs without modifying the underlying stylometric baseline algorithm.
Produces auditable metrics, subgroup breakdowns, feature associations,
and negative-control false-positive analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ateval.detection import (
    DetectionRecord,
    analyze_feature_associations,
    bootstrap_proportion_ci,
    evaluate_by_subgroup,
    evaluate_mixed_authorship_cohort,
    evaluate_records,
    find_optimal_threshold,
)

MANIFEST_DIR = Path("data/manifests")
REPORT_DIR = Path("reports/milestone5_1")


def _load_manifest_records(manifest_path: Path) -> list[DetectionRecord]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [DetectionRecord.from_dict(r) for r in data.get("records", [])]


def run_benchmark(
    manifest_dir: Path = MANIFEST_DIR,
    report_dir: Path = REPORT_DIR,
    *,
    seed: int = 42,
) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)

    val_path = manifest_dir / "txd22_val_manifest.json"
    test_path = manifest_dir / "txd22_test_manifest.json"
    length_matched_path = manifest_dir / "txd22_length_matched_test.json"
    mixed_path = manifest_dir / "txd22_mixed_authorship_manifest.json"

    val_records = _load_manifest_records(val_path)
    test_records = _load_manifest_records(test_path)
    print(f"Loaded {len(val_records):,} validation records and {len(test_records):,} test records.")

    # 1. Threshold selection on validation split ONLY
    val_scores = []
    val_labels = []
    for r in val_records:
        if r.label == "human":
            y = 0
        elif r.label == "ai":
            y = 1
        else:
            continue
        from ateval.detectors import evaluate_stylometric_baseline
        res = evaluate_stylometric_baseline(r.text)
        val_scores.append(float(res["signal_score"]))
        val_labels.append(y)

    optimal_threshold = find_optimal_threshold(val_scores, val_labels, metric="youden")
    print(f"Optimal threshold selected on validation set (Youden's J): {optimal_threshold}")

    # 2. Main Task A Evaluation on Test Set
    test_metrics, test_details = evaluate_records(
        test_records,
        threshold=optimal_threshold,
        run_bootstrap=True,
        seed=seed,
    )
    print("Test Set Metrics (Task A):")
    print(f"  Total samples: {test_metrics.total_samples:,} (AI: {test_metrics.positive_count:,}, Human: {test_metrics.negative_count:,})")
    print(f"  AUROC: {test_metrics.auroc:.4f} (95% CI: {test_metrics.ci_auroc[0]:.4f} - {test_metrics.ci_auroc[1]:.4f})")
    print(f"  AUPRC: {test_metrics.auprc:.4f}")
    print(f"  Precision: {test_metrics.precision:.4f}, Recall: {test_metrics.recall:.4f}, F1: {test_metrics.f1:.4f}")
    print(f"  False Positive Rate (FPR): {test_metrics.false_positive_rate:.4f} (95% CI: {test_metrics.ci_fpr[0]:.4f} - {test_metrics.ci_fpr[1]:.4f})")
    print(f"  False Negative Rate (FNR): {test_metrics.false_negative_rate:.4f} (95% CI: {test_metrics.ci_fnr[0]:.4f} - {test_metrics.ci_fnr[1]:.4f})")

    # 3. Length-matched evaluation
    length_matched_records = _load_manifest_records(length_matched_path) if length_matched_path.exists() else []
    if length_matched_records:
        lm_metrics, _ = evaluate_records(length_matched_records, threshold=optimal_threshold, run_bootstrap=True, seed=seed)
        print(f"Length-Matched Test Metrics: AUROC={lm_metrics.auroc:.4f}, F1={lm_metrics.f1:.4f}, FPR={lm_metrics.false_positive_rate:.4f}")
        length_matched_summary = lm_metrics.to_dict()
    else:
        length_matched_summary = {"note": "No length-matched test records available"}

    # 4. Feature association analysis
    feature_associations = analyze_feature_associations(test_details)
    print("\nFeature Association Analysis (Point-Biserial Correlation with AI label):")
    for feat, stats in feature_associations.items():
        print(f"  {feat:28s}: r_pb={stats['point_biserial_correlation']:+.4f} (Human mean={stats['human_mean']:.4f}, AI mean={stats['ai_mean']:.4f})")

    # 5. Performance by length group
    by_length = evaluate_by_subgroup(test_records, lambda r: r.length_group(), threshold=optimal_threshold)

    # 6. Performance by generator model
    by_model = evaluate_by_subgroup(
        test_records,
        lambda r: (r.generator_model or "human"),
        threshold=optimal_threshold,
    )

    # 7. Task B: Mixed authorship analysis
    mixed_records = _load_manifest_records(mixed_path) if mixed_path.exists() else []
    mixed_analysis = evaluate_mixed_authorship_cohort(mixed_records) if mixed_records else {"total_mixed": 0}

    # 8. Phase 6: Negative-control false positive analysis on human text
    human_records = [r for r in test_records if r.label == "human"]
    human_details = [d for d in test_details if d["label"] == "human"]
    fp_count = sum(1 for d in human_details if d["signal_score"] >= optimal_threshold)
    human_fpr = fp_count / len(human_details) if human_details else 0.0

    # Human text false positives by length
    human_by_length = defaultdict(list)
    for d in human_details:
        w = d["word_count"]
        grp = "<100" if w < 100 else ("100-200" if w <= 200 else ("201-300" if w <= 300 else ">300"))
        human_by_length[grp].append(d["signal_score"] >= optimal_threshold)

    human_length_fpr = {
        grp: {
            "count": len(flags),
            "false_positives": sum(flags),
            "false_positive_rate": round(sum(flags) / len(flags), 4) if flags else 0.0,
        }
        for grp, flags in human_by_length.items()
    }

    negative_control_report = {
        "negative_cohort_source": "TXD-22 Human Academic/Professional Responses (~350 participants)",
        "human_samples_evaluated": len(human_details),
        "false_positive_count": fp_count,
        "overall_false_positive_rate": round(human_fpr, 4),
        "ci_fpr_95": bootstrap_proportion_ci(
            [d["signal_score"] >= optimal_threshold for d in human_details],
            seed=seed,
        ),
        "false_positive_by_length_bin": human_length_fpr,
        "interpretation": (
            "Stylometric features such as low sentence-length variation and high vocabulary uniformity "
            "can occur naturally in concise scholarly writing, leading to false positives on human prose."
        ),
    }

    full_report = {
        "benchmark_metadata": {
            "evaluator_name": "stylometric-baseline",
            "evaluator_version": "m5.0.0",
            "benchmark_task": "Task A (Human vs AI Binary), Task B (Mixed Authorship)",
            "validation_threshold": optimal_threshold,
            "threshold_selection_criterion": "Youden's J statistic on validation split",
        },
        "task_a_test_metrics": test_metrics.to_dict(),
        "length_matched_test_metrics": length_matched_summary,
        "feature_associations": feature_associations,
        "performance_by_length_bin": by_length,
        "performance_by_generator_model": by_model,
        "task_b_mixed_authorship_analysis": mixed_analysis,
        "phase_6_negative_control_false_positives": negative_control_report,
        "limitations_and_scientific_honesty": [
            "The stylometric signal is a heuristic diagnostic and must NOT be converted into an authorship probability.",
            "Features are sensitive to text length, topic formality, and discipline conventions.",
            "No calibrated claim is made without separate external calibration on targeted domain texts.",
        ],
    }

    out_file = report_dir / "baseline_benchmark_results.json"
    out_file.write_text(json.dumps(full_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nFull benchmark report written to {out_file}")
    return full_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR, help="Manifest directory")
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR, help="Report output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    try:
        run_benchmark(args.manifest_dir, args.report_dir, seed=args.seed)
    except Exception as exc:
        print(f"Benchmark error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
