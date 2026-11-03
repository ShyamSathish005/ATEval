"""ATEval detection benchmark and dataset qualification package."""

from .adapters import M4Adapter, RAIDAdapter, SyntheticDetectionFixture, TXD22Adapter, compute_sha256
from .benchmark_tasks import (
    TaskDefinitionError,
    prepare_task_a_cohort,
    prepare_task_b_cohort,
    prepare_task_c_domain_cohort,
    prepare_task_d_passage_cohort,
)
from .evaluation import (
    EvaluationMetrics,
    analyze_feature_associations,
    bootstrap_ci,
    calculate_auprc,
    calculate_auroc,
    calculate_classification_metrics,
    evaluate_by_subgroup,
    evaluate_mixed_authorship_cohort,
    evaluate_records,
    find_optimal_threshold,
)
from .schema import (
    AuthorshipClass,
    DatasetManifest,
    DetectionRecord,
    SpanAnnotation,
    TaskKind,
)
from .splits import (
    SplitConfig,
    SplitResult,
    create_leakage_resistant_splits,
    create_length_matched_cohort,
)

__all__ = [
    "AuthorshipClass",
    "DatasetManifest",
    "DetectionRecord",
    "EvaluationMetrics",
    "M4Adapter",
    "RAIDAdapter",
    "SpanAnnotation",
    "SplitConfig",
    "SplitResult",
    "SyntheticDetectionFixture",
    "TXD22Adapter",
    "TaskDefinitionError",
    "TaskKind",
    "analyze_feature_associations",
    "bootstrap_ci",
    "calculate_auprc",
    "calculate_auroc",
    "calculate_classification_metrics",
    "compute_sha256",
    "create_leakage_resistant_splits",
    "create_length_matched_cohort",
    "evaluate_by_subgroup",
    "evaluate_mixed_authorship_cohort",
    "evaluate_records",
    "find_optimal_threshold",
    "prepare_task_a_cohort",
    "prepare_task_b_cohort",
    "prepare_task_c_domain_cohort",
    "prepare_task_d_passage_cohort",
]

