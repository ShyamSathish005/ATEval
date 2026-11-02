"""Document-held-out classical intention baselines using scikit-learn."""

from __future__ import annotations

import hashlib
import json
import platform
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .schema import RevisionRecord


def context_text(record: RevisionRecord, level: str = "local") -> str:
    """Build bounded features from source text and optional available context."""
    section = record.section_type or "unknown"
    if level == "sentence":
        return f"SECTION_{section} {record.original_text}"
    if level == "local":
        return f"SECTION_{section} CONTEXT_BEFORE {record.context_before} TARGET {record.original_text} CONTEXT_AFTER {record.context_after}"
    if level == "document":
        full = str(record.metadata.get("document_context", ""))
        return f"SECTION_{section} DOCUMENT_CONTEXT {full or (record.context_before + ' ' + record.original_text + ' ' + record.context_after)}"
    raise ValueError("context level must be sentence, local, or document")


def _dependencies():
    try:
        import sklearn
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedGroupKFold
        from sklearn.pipeline import FeatureUnion, Pipeline
        from sklearn.svm import LinearSVC
    except ImportError as exc:
        raise RuntimeError("Install the classical ML extras with: python -m pip install -e '.[revision-ml]'") from exc
    return sklearn, CalibratedClassifierCV, FeatureUnion, TfidfVectorizer, LogisticRegression, StratifiedGroupKFold, Pipeline, LinearSVC


def _features(records: list[RevisionRecord], context_level: str) -> list[str]:
    return [context_text(record, context_level) for record in records]


def _labels(records: list[RevisionRecord]) -> list[str]:
    labels = []
    for record in records:
        if not record.canonical_labels:
            labels.append("__unlabeled__")
        else:
            labels.append(record.canonical_labels[0])
    return labels


def _macro_weighted(gold: list[str], predicted: list[str], labels: list[str]) -> dict[str, Any]:
    per_class = {}
    f1s, weighted = [], 0.0
    total = len(gold)
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, predicted))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted))
        support = sum(g == label for g in gold)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        f1s.append(f1)
        weighted += f1 * support
    return {"count": total, "accuracy": sum(g == p for g, p in zip(gold, predicted)) / total if total else None, "macro_f1": sum(f1s) / len(f1s) if f1s else None, "weighted_f1": weighted / total if total else None, "per_class": per_class, "confusion": {f"{g}→{p}": sum(x == g and y == p for x, y in zip(gold, predicted)) for g in labels for p in labels if any(x == g and y == p for x, y in zip(gold, predicted))}}


def _calibration(gold: list[str], classes: list[str], probabilities: list[list[float]], bins: int = 10) -> dict[str, Any]:
    if not gold:
        return {"expected_calibration_error": None, "multiclass_brier": None}
    confidence, correct = [], []
    class_index = {label: i for i, label in enumerate(classes)}
    brier = 0.0
    for label, row in zip(gold, probabilities):
        chosen = max(range(len(row)), key=row.__getitem__)
        confidence.append(row[chosen])
        correct.append(classes[chosen] == label)
        brier += sum((score - (1.0 if classes[i] == label else 0.0)) ** 2 for i, score in enumerate(row))
    ece = 0.0
    for bucket in range(bins):
        lo, hi = bucket / bins, (bucket + 1) / bins
        indices = [i for i, value in enumerate(confidence) if lo <= value < hi or (bucket == bins - 1 and value == 1.0)]
        if indices:
            ece += len(indices) / len(gold) * abs(sum(confidence[i] for i in indices) / len(indices) - sum(correct[i] for i in indices) / len(indices))
    return {"expected_calibration_error_10_bins": ece, "multiclass_brier": brier / len(gold), "interpretation": "calibration estimates on the held-out test set; not a guarantee for deployment"}


def _score_predictions(gold: list[str], predicted: list[str], labels: list[str], probabilities: list[list[float]], *, calibrated: bool) -> dict[str, Any]:
    metrics = _macro_weighted(gold, predicted, labels)
    metrics["calibration"] = _calibration(gold, labels, probabilities)
    metrics["calibrated"] = calibrated
    if not calibrated:
        metrics["calibration"]["interpretation"] = "LogisticRegression predict_proba; no separate probability calibration was applied"
    return metrics


def _make_pipeline(kind: str, C: float, seed: int, *, calibrate_svm: bool = True):
    sklearn, CalibratedClassifierCV, FeatureUnion, TfidfVectorizer, LogisticRegression, StratifiedGroupKFold, Pipeline, LinearSVC = _dependencies()
    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True, strip_accents="unicode", max_features=12_000)),
        ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=3, sublinear_tf=True, max_features=12_000)),
    ])
    if kind == "logistic_regression":
        model = LogisticRegression(C=C, class_weight="balanced", max_iter=600, random_state=seed, solver="lbfgs", tol=1e-3)
    elif kind == "linear_svm":
        model = LinearSVC(C=C, class_weight="balanced", random_state=seed, max_iter=5000)
        # Grouped CV creates calibrated outputs while keeping a document's
        # sentences together in every calibration fold.
        if calibrate_svm:
            model = CalibratedClassifierCV(model, method="sigmoid", cv=3, ensemble=True)
    else:
        raise ValueError(f"Unknown classifier: {kind}")
    return Pipeline([("tfidf", features), ("classifier", model)])


def _fit_model(kind: str, C: float, train: list[RevisionRecord], context_level: str, seed: int, *, calibrate_svm: bool = True):
    model = _make_pipeline(kind, C, seed, calibrate_svm=calibrate_svm)
    x = _features(train, context_level)
    y = _labels(train)
    if kind == "linear_svm" and calibrate_svm:
        import numpy as np
        StratifiedGroupKFold = _dependencies()[5]
        splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
        groups = [record.source_document_id for record in train]
        folds = list(splitter.split(np.zeros(len(y)), y, groups))
        model.named_steps["classifier"].cv = folds
        model.fit(x, y)
    else:
        model.fit(x, y)
    return model


def _predict(model: Any, records: list[RevisionRecord], context_level: str, labels: list[str]) -> tuple[list[str], list[list[float]]]:
    x = _features(records, context_level)
    predicted = list(map(str, model.predict(x)))
    raw_probs = model.predict_proba(x)
    classes = list(map(str, model.named_steps["classifier"].classes_))
    class_index = {label: i for i, label in enumerate(classes)}
    probabilities = [[float(raw_probs[row, class_index[label]]) if label in class_index else 0.0 for label in labels] for row in range(len(records))]
    return predicted, probabilities


def majority_report(train: list[RevisionRecord], test: list[RevisionRecord], labels: list[str]) -> dict[str, Any]:
    counts = Counter(_labels(train))
    counts.pop("__unlabeled__", None)
    if not counts:
        raise ValueError("No labeled training records for majority baseline")
    majority = counts.most_common(1)[0][0]
    gold = _labels(test)
    return {"model": "majority_class", "majority_label": majority, **_macro_weighted(gold, [majority] * len(gold), labels)}


def train_compare(
    train: list[RevisionRecord], dev: list[RevisionRecord], test: list[RevisionRecord], *,
    output_dir: str | Path, seed: int = 17, context_levels: tuple[str, ...] = ("sentence", "local", "document"),
) -> dict[str, Any]:
    """Tune only on validation; save held-out comparison and model artifacts."""
    _dependencies()
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite experiment directory: {output}")
    if any(not record.license_verified for record in train):
        raise ValueError("Training records include unverified licenses")
    overlap = set(record.source_document_id for record in train) & set(record.source_document_id for record in dev + test)
    if overlap:
        raise ValueError(f"Source-document leakage across train/dev/test: {sorted(overlap)[:10]}")
    if not train or not dev or not test:
        raise ValueError("All train, development, and held-out test partitions must contain records")
    source_counts = {name: len(records) for name, records in (("train", train), ("dev", dev), ("test", test))}
    def is_noop(record: RevisionRecord) -> bool:
        original = " ".join(unicodedata.normalize("NFKC", record.original_text).casefold().split())
        revised = " ".join(unicodedata.normalize("NFKC", record.revised_text).casefold().split())
        return original == revised
    no_op_counts = {name: sum(is_noop(record) for record in records) for name, records in (("train", train), ("dev", dev), ("test", test))}
    train, dev, test = ([record for record in records if not is_noop(record)] for records in (train, dev, test))
    _ = platform.python_version()
    train_labels, dev_labels, test_labels = _labels(train), _labels(dev), _labels(test)
    labels = sorted(set(train_labels + dev_labels + test_labels) - {"__unlabeled__"})
    report: dict[str, Any] = {
        "schema": "ateval-revision-baselines-v1",
        "seed": seed,
        "split_document_counts": {name: len({r.source_document_id for r in records}) for name, records in (("train", train), ("dev", dev), ("test", test))},
        "split_record_counts": {"train": len(train), "dev": len(dev), "test": len(test)},
        "source_record_counts_before_noop_filter": source_counts,
        "exact_text_noop_records_excluded_from_intent_task": no_op_counts,
        "source_document_leakage": False,
        "labels": labels,
        "models": {},
    }
    report["models"]["majority"] = majority_report(train, test, labels)
    best_models = {}
    sklearn, CalibratedClassifierCV, FeatureUnion, TfidfVectorizer, LogisticRegression, StratifiedGroupKFold, Pipeline, LinearSVC = _dependencies()
    for context_level in context_levels:
        report["models"][context_level] = {}
        vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True, strip_accents="unicode", max_features=12_000)),
            ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=3, sublinear_tf=True, max_features=12_000)),
        ])
        x_train = vectorizer.fit_transform(_features(train, context_level))
        x_dev = vectorizer.transform(_features(dev, context_level))
        x_test = vectorizer.transform(_features(test, context_level))
        for kind in ("logistic_regression", "linear_svm"):
            trials = []
            for C in (0.5, 2.0):
                if kind == "logistic_regression":
                    candidate = LogisticRegression(C=C, class_weight="balanced", max_iter=600, random_state=seed, solver="lbfgs", tol=1e-3)
                else:
                    candidate = LinearSVC(C=C, class_weight="balanced", random_state=seed, max_iter=1200)
                candidate.fit(x_train, train_labels)
                prediction = list(map(str, candidate.predict(x_dev)))
                score = _macro_weighted(dev_labels, prediction, labels)["macro_f1"]
                trials.append((score or 0.0, C))
            _, best_C = max(trials, key=lambda item: (item[0], -item[1]))
            if kind == "logistic_regression":
                classifier = LogisticRegression(C=best_C, class_weight="balanced", max_iter=600, random_state=seed, solver="lbfgs", tol=1e-3)
                classifier.fit(x_train, train_labels)
            else:
                base = LinearSVC(C=best_C, class_weight="balanced", random_state=seed, max_iter=1200)
                import numpy as np
                splitter = StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=seed)
                folds = list(splitter.split(np.zeros(len(train_labels)), train_labels, [record.source_document_id for record in train]))
                classifier = CalibratedClassifierCV(base, method="sigmoid", cv=folds, ensemble=True)
                classifier.fit(x_train, train_labels)
            predicted = list(map(str, classifier.predict(x_test)))
            classifier_classes = list(map(str, classifier.classes_))
            class_index = {label: i for i, label in enumerate(classifier_classes)}
            raw_probs = classifier.predict_proba(x_test)
            probabilities = [[float(raw_probs[row, class_index[label]]) if label in class_index else 0.0 for label in labels] for row in range(len(test))]
            metrics = _score_predictions(test_labels, predicted, labels, probabilities, calibrated=kind == "linear_svm")
            metrics["selected_C_by_dev_macro_f1"] = best_C
            final_model = Pipeline([("tfidf", vectorizer), ("classifier", classifier)])
            report["models"][context_level][kind] = metrics
            domain_results = {}
            domain_values = [str(record.metadata.get("domain") or "unknown") for record in test]
            for domain in sorted(set(domain_values)):
                indexes = [index for index, value in enumerate(domain_values) if value == domain]
                domain_results[domain] = {
                    "n": len(indexes),
                    "metrics": _score_predictions(
                        [test_labels[index] for index in indexes],
                        [predicted[index] for index in indexes],
                        labels,
                        [probabilities[index] for index in indexes],
                        calibrated=kind == "linear_svm",
                    ),
                }
            report["models"][context_level][kind]["test_by_domain"] = domain_results
            best_models[(context_level, kind)] = final_model
    output.mkdir(parents=True)
    from joblib import dump
    import sklearn
    source_files = [Path(__file__), Path(__file__).with_name("datasets.py"), Path(__file__).with_name("taxonomy.py"), Path(__file__).with_name("schema.py")]
    source_digest = hashlib.sha256("".join(_hash for _hash in (hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files)).encode()).hexdigest()
    dataset_manifest_path = Path("data/manifests/revision_training_manifest.json")
    dataset_manifest_hash = hashlib.sha256(dataset_manifest_path.read_bytes()).hexdigest() if dataset_manifest_path.exists() else None
    for (context_level, kind), model in best_models.items():
        path = output / f"{context_level}-{kind}.joblib"
        dump(model, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        (output / f"{context_level}-{kind}.metadata.json").write_text(json.dumps({
            "schema": "ateval-revision-classifier-metadata-v1", "model_type": kind,
            "context_level": context_level, "training_records": len(train),
            "training_source_document_ids": sorted({r.source_document_id for r in train}),
            "seed": seed, "selected_C_by_dev_macro_f1": report["models"][context_level][kind]["selected_C_by_dev_macro_f1"],
            "sklearn_version": sklearn.__version__, "python_version": platform.python_version(), "training_platform": platform.platform(),
            "weight_file": path.name, "sha256": digest, "label_order": labels,
            "dataset_manifest": "data/manifests/revision_training_manifest.json", "dataset_manifest_sha256": dataset_manifest_hash,
            "source_code_sha256": source_digest,
            "feature_config": {"word_tfidf": {"analyzer": "word", "ngram_range": [1, 2], "max_features": 12000}, "char_tfidf": {"analyzer": "char", "ngram_range": [3, 5], "min_df": 3, "max_features": 12000}},
            "calibration": "sigmoid/Platt through 2-fold stratified document-grouped CV" if kind == "linear_svm" else "uncalibrated LogisticRegression predict_proba; ECE reported",
            "security_note": "Only load artifacts created and controlled by this workspace; joblib files use pickle serialization.",
        }, indent=2) + "\n", encoding="utf-8")
    (output / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
