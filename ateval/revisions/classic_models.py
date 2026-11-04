"""Document-held-out classical intention baselines using scikit-learn."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .schema import RevisionRecord

DECLARATIVE_MODEL_SCHEMA = "ateval-revision-declarative-model-v1"
METADATA_SCHEMA = "ateval-revision-classifier-metadata-v2"
ALLOWED_MODEL_ROOT = Path(__file__).resolve().parents[2] / "models" / "revisions"
# Build-pinned integrity digest map for official bundled artifacts (when shipped).
PINNED_MODEL_DIGESTS: dict[str, str] = {}
_WORD_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")


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
    import sklearn
    source_files = [Path(__file__), Path(__file__).with_name("datasets.py"), Path(__file__).with_name("taxonomy.py"), Path(__file__).with_name("schema.py")]
    source_digest = hashlib.sha256("".join(_hash for _hash in (hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files)).encode()).hexdigest()
    dataset_manifest_path = Path("data/manifests/revision_training_manifest.json")
    dataset_manifest_hash = hashlib.sha256(dataset_manifest_path.read_bytes()).hexdigest() if dataset_manifest_path.exists() else None
    for (context_level, kind), model in best_models.items():
        path = output / f"{context_level}-{kind}.model.json"
        save_declarative_model(model, path, context_level=context_level, kind=kind)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        (output / f"{context_level}-{kind}.metadata.json").write_text(json.dumps({
            "schema": METADATA_SCHEMA, "model_type": kind,
            "context_level": context_level, "training_records": len(train),
            "training_source_document_ids": sorted({r.source_document_id for r in train}),
            "seed": seed, "selected_C_by_dev_macro_f1": report["models"][context_level][kind]["selected_C_by_dev_macro_f1"],
            "sklearn_version": sklearn.__version__, "python_version": platform.python_version(), "training_platform": platform.platform(),
            "weight_file": path.name, "sha256": digest, "label_order": labels,
            "dataset_manifest": "data/manifests/revision_training_manifest.json", "dataset_manifest_sha256": dataset_manifest_hash,
            "source_code_sha256": source_digest,
            "feature_config": {"word_tfidf": {"analyzer": "word", "ngram_range": [1, 2], "max_features": 12000}, "char_tfidf": {"analyzer": "char", "ngram_range": [3, 5], "min_df": 3, "max_features": 12000}},
            "calibration": "sigmoid/Platt through 2-fold stratified document-grouped CV" if kind == "linear_svm" else "uncalibrated LogisticRegression predict_proba; ECE reported",
            "security_note": "Declarative JSON model format (vocabulary + numeric weights). No pickle or joblib deserialization is used. File hash checks verify integrity on disk but are not a sandbox against code already running inside the process.",
        }, indent=2) + "\n", encoding="utf-8")
    (output / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def _strip_accents_unicode(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    if normalized == text:
        return text
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _extract_word_ngrams(text: str, ngram_range: tuple[int, int]) -> Counter[str]:
    clean = _strip_accents_unicode(text).lower()
    tokens = _WORD_TOKEN_RE.findall(clean)
    counts: Counter[str] = Counter()
    min_n, max_n = ngram_range
    n_tokens = len(tokens)
    for n in range(min_n, max_n + 1):
        if n == 1:
            counts.update(tokens)
        else:
            for idx in range(n_tokens - n + 1):
                counts[" ".join(tokens[idx : idx + n])] += 1
    return counts


def _extract_char_ngrams(text: str, ngram_range: tuple[int, int]) -> Counter[str]:
    clean = re.sub(r"\s+", " ", text.lower())
    counts: Counter[str] = Counter()
    min_n, max_n = ngram_range
    text_len = len(clean)
    for n in range(min_n, max_n + 1):
        for idx in range(text_len - n + 1):
            counts[clean[idx : idx + n]] += 1
    return counts


class DeclarativeLinearModel:
    """Safe declarative TF-IDF + linear classifier reconstructed from validated JSON."""

    def __init__(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict) or payload.get("schema") != DECLARATIVE_MODEL_SCHEMA:
            raise ValueError("Invalid declarative model schema")
        classes = payload.get("classes")
        if not isinstance(classes, list) or not classes or not all(isinstance(c, str) and c for c in classes):
            raise ValueError("Declarative model must define non-empty string classes")
        self.classes_: list[str] = list(classes)
        self.model_type: str = str(payload.get("model_type", "logistic_regression"))
        self.context_level: str = str(payload.get("context_level", "local"))

        word_cfg = payload.get("word_tfidf")
        char_cfg = payload.get("char_tfidf")
        if not isinstance(word_cfg, dict) or not isinstance(char_cfg, dict):
            raise ValueError("Declarative model is missing TF-IDF configuration")
        self._word_vocab, self._word_idf, self._word_ngram, self._word_sublinear = self._validate_tfidf_block(word_cfg, "word_tfidf")
        self._char_vocab, self._char_idf, self._char_ngram, self._char_sublinear = self._validate_tfidf_block(char_cfg, "char_tfidf")
        self._n_features = len(self._word_idf) + len(self._char_idf)

        clf = payload.get("classifier")
        if not isinstance(clf, dict):
            raise ValueError("Declarative model is missing classifier weights")
        coef = clf.get("coef")
        intercept = clf.get("intercept")
        if not isinstance(coef, list) or not isinstance(intercept, list) or not coef or len(coef) != len(intercept):
            raise ValueError("Classifier coef and intercept dimensions are invalid")
        n_rows = len(coef)
        if len(self.classes_) == 2 and n_rows != 1:
            raise ValueError("Binary linear classifier must have 1 coefficient row")
        if len(self.classes_) > 2 and n_rows != len(self.classes_):
            raise ValueError("Multiclass linear classifier row count must match class count")
        self._coef: list[list[float]] = []
        for row in coef:
            if not isinstance(row, list) or len(row) != self._n_features:
                raise ValueError("Classifier coefficient vector length does not match TF-IDF feature count")
            self._coef.append([self._finite_float(val, "coef") for val in row])
        self._intercept: list[float] = [self._finite_float(val, "intercept") for val in intercept]

    @staticmethod
    def _finite_float(value: Any, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Non-numeric value in {field}")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"Non-finite float in {field}")
        return result

    def _validate_tfidf_block(
        self, block: dict[str, Any], name: str
    ) -> tuple[dict[str, int], list[float], tuple[int, int], bool]:
        vocab = block.get("vocabulary")
        idf = block.get("idf")
        ngram = block.get("ngram_range", [1, 2])
        sublinear = bool(block.get("sublinear_tf", True))
        if not isinstance(vocab, dict) or not isinstance(idf, list) or len(vocab) != len(idf):
            raise ValueError(f"Invalid vocabulary/idf in {name}")
        if not isinstance(ngram, list) or len(ngram) != 2 or not all(isinstance(x, int) and 1 <= x <= 10 for x in ngram) or ngram[0] > ngram[1]:
            raise ValueError(f"Invalid ngram_range in {name}")
        idf_floats = [self._finite_float(x, f"{name}.idf") for x in idf]
        n = len(idf_floats)
        clean_vocab: dict[str, int] = {}
        seen_indices: set[int] = set()
        for token, idx in vocab.items():
            if not isinstance(token, str) or isinstance(idx, bool) or not isinstance(idx, int) or not (0 <= idx < n):
                raise ValueError(f"Invalid vocabulary entry in {name}")
            seen_indices.add(idx)
            clean_vocab[token] = idx
        if len(seen_indices) != n:
            raise ValueError(f"Vocabulary indices in {name} are not a bijection")
        return clean_vocab, idf_floats, (int(ngram[0]), int(ngram[1])), sublinear

    def _vectorize_one(self, text: str) -> dict[int, float]:
        sparse: dict[int, float] = {}
        word_counts = _extract_word_ngrams(text, self._word_ngram)
        word_sq_sum = 0.0
        word_vec: dict[int, float] = {}
        for term, count in word_counts.items():
            idx = self._word_vocab.get(term)
            if idx is not None and count > 0:
                tf = (1.0 + math.log(count)) if self._word_sublinear else float(count)
                val = tf * self._word_idf[idx]
                word_vec[idx] = val
                word_sq_sum += val * val
        if word_sq_sum > 0.0:
            norm = math.sqrt(word_sq_sum)
            for idx, val in word_vec.items():
                sparse[idx] = val / norm

        char_offset = len(self._word_idf)
        char_counts = _extract_char_ngrams(text, self._char_ngram)
        char_sq_sum = 0.0
        char_vec: dict[int, float] = {}
        for term, count in char_counts.items():
            idx = self._char_vocab.get(term)
            if idx is not None and count > 0:
                tf = (1.0 + math.log(count)) if self._char_sublinear else float(count)
                val = tf * self._char_idf[idx]
                char_vec[char_offset + idx] = val
                char_sq_sum += val * val
        if char_sq_sum > 0.0:
            norm = math.sqrt(char_sq_sum)
            for idx, val in char_vec.items():
                sparse[idx] = val / norm
        return sparse

    def predict_proba(self, features: Iterable[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in features:
            vec = self._vectorize_one(str(text))
            logits: list[float] = []
            for row, intercept in zip(self._coef, self._intercept):
                score = intercept
                for idx, val in vec.items():
                    score += row[idx] * val
                logits.append(score)
            if len(self.classes_) == 2:
                z = logits[0]
                p1 = 1.0 / (1.0 + math.exp(-max(-500.0, min(500.0, z))))
                results.append([1.0 - p1, p1])
            else:
                max_z = max(logits)
                exps = [math.exp(z - max_z) for z in logits]
                total = sum(exps) or 1.0
                results.append([val / total for val in exps])
        return results

    def predict(self, features: Iterable[str]) -> list[str]:
        probs = self.predict_proba(features)
        return [self.classes_[max(range(len(row)), key=row.__getitem__)] for row in probs]


def save_declarative_model(pipeline: Any, path: str | Path, *, context_level: str = "local", kind: str = "logistic_regression") -> dict[str, Any]:
    """Serialize a fitted scikit-learn TF-IDF + linear pipeline to a declarative JSON file."""
    target = Path(path)
    tfidf_union = pipeline.named_steps["tfidf"]
    transformers = dict(tfidf_union.transformer_list)
    word_vec = transformers["word"]
    char_vec = transformers["char"]
    clf = pipeline.named_steps["classifier"]
    if hasattr(clf, "coef_") and hasattr(clf, "intercept_"):
        coef = [[float(x) for x in row] for row in clf.coef_.tolist()]
        intercept = [float(x) for x in clf.intercept_.tolist()]
        classes = [str(c) for c in clf.classes_.tolist()]
    elif hasattr(clf, "calibrated_classifiers_") and clf.calibrated_classifiers_:
        # Average linear parameters across calibrated folds for declarative export
        classes = [str(c) for c in clf.classes_.tolist()]
        first_est = clf.calibrated_classifiers_[0].estimator
        n_rows, n_cols = first_est.coef_.shape
        coef = [[0.0] * n_cols for _ in range(n_rows)]
        intercept = [0.0] * len(first_est.intercept_)
        count = len(clf.calibrated_classifiers_)
        for cal in clf.calibrated_classifiers_:
            est_coef = cal.estimator.coef_.tolist()
            est_int = cal.estimator.intercept_.tolist()
            for r in range(n_rows):
                intercept[r] += float(est_int[r]) / count
                for c in range(n_cols):
                    coef[r][c] += float(est_coef[r][c]) / count
    else:
        raise ValueError(f"Unsupported classifier for declarative serialization: {type(clf).__name__}")

    payload = {
        "schema": DECLARATIVE_MODEL_SCHEMA,
        "model_type": kind,
        "context_level": context_level,
        "classes": classes,
        "word_tfidf": {
            "ngram_range": list(word_vec.ngram_range),
            "sublinear_tf": bool(word_vec.sublinear_tf),
            "vocabulary": {str(k): int(v) for k, v in word_vec.vocabulary_.items()},
            "idf": [float(x) for x in word_vec.idf_.tolist()],
        },
        "char_tfidf": {
            "ngram_range": list(char_vec.ngram_range),
            "sublinear_tf": bool(char_vec.sublinear_tf),
            "vocabulary": {str(k): int(v) for k, v in char_vec.vocabulary_.items()},
            "idf": [float(x) for x in char_vec.idf_.tolist()],
        },
        "classifier": {
            "coef": coef,
            "intercept": intercept,
        },
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload


def load_declarative_model(
    model_path: str | Path,
    metadata_path: str | Path | None = None,
    *,
    allowed_root: str | Path | None = ALLOWED_MODEL_ROOT,
    expected_sha256: str | None = None,
) -> DeclarativeLinearModel:
    """Safely validate and load a declarative JSON revision intent model without pickle/joblib."""
    resolved_model = Path(model_path).expanduser().resolve()
    if resolved_model.suffix == ".joblib":
        raise ValueError("Refusing to load executable .joblib/pickle model artifact; use declarative .model.json format")
    if allowed_root is not None:
        root_resolved = Path(allowed_root).expanduser().resolve()
        try:
            resolved_model.relative_to(root_resolved)
        except ValueError as exc:
            raise ValueError(f"Model artifact path {resolved_model} is outside the trusted model directory") from exc
    if not resolved_model.is_file():
        raise FileNotFoundError(f"Model artifact not found: {resolved_model}")
    if metadata_path is None:
        stem = resolved_model.name[:-11] if resolved_model.name.endswith(".model.json") else resolved_model.stem
        resolved_meta = resolved_model.with_name(f"{stem}.metadata.json")
    else:
        resolved_meta = Path(metadata_path).expanduser().resolve()
        if allowed_root is not None:
            try:
                resolved_meta.relative_to(Path(allowed_root).expanduser().resolve())
            except ValueError as exc:
                raise ValueError("Model metadata path is outside the trusted model directory") from exc
    if not resolved_meta.is_file():
        raise FileNotFoundError(f"Model metadata manifest not found: {resolved_meta}")
    try:
        metadata = json.loads(resolved_meta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Model metadata manifest is not valid JSON") from exc
    if not isinstance(metadata, dict) or metadata.get("schema") not in {
        METADATA_SCHEMA,
        "ateval-revision-classifier-metadata-v1",
    }:
        raise ValueError("Invalid model metadata schema")
    if metadata.get("weight_file") != resolved_model.name:
        raise ValueError("Model metadata weight_file does not match artifact filename")
    label_order = metadata.get("label_order")
    if not isinstance(label_order, list) or not label_order:
        raise ValueError("Model metadata is missing valid label_order")

    raw_bytes = resolved_model.read_bytes()
    actual_digest = hashlib.sha256(raw_bytes).hexdigest()
    meta_digest = metadata.get("sha256")
    if not isinstance(meta_digest, str) or len(meta_digest) != 64 or actual_digest != meta_digest:
        raise ValueError("Intent model SHA-256 digest does not match its metadata manifest")
    pinned = expected_sha256 or PINNED_MODEL_DIGESTS.get(resolved_model.name)
    if pinned and actual_digest != pinned:
        raise ValueError("Intent model SHA-256 digest does not match the build-pinned digest")

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Declarative model artifact is not valid UTF-8 JSON") from exc
    model = DeclarativeLinearModel(payload)
    if sorted(model.classes_) != sorted(str(item) for item in label_order):
        raise ValueError("Declarative model classes do not match metadata label_order")
    return model
