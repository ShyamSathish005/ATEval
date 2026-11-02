"""Lightweight, CPU-only Naive Bayes intention baseline."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .schema import RevisionRecord

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'-]*|\d+(?:\.\d+)?")


def _features(original: str, revised: str) -> Counter[str]:
    before = [match.group(0).casefold() for match in TOKEN_RE.finditer(original)]
    after = [match.group(0).casefold() for match in TOKEN_RE.finditer(revised)]
    old, new = Counter(before), Counter(after)
    features: Counter[str] = Counter()
    features.update(f"src:{token}" for token in before)
    features.update(f"tgt:{token}" for token in after)
    features.update(f"added:{token}" for token, count in (new - old).items() for _ in range(min(count, 3)))
    features.update(f"removed:{token}" for token, count in (old - new).items() for _ in range(min(count, 3)))
    features[f"change_ratio:{min(9, int(10 * (sum((old - new).values()) + sum((new - old).values())) / max(1, len(before))))}"] += 1
    return features


class MultinomialIntentModel:
    """Small explainable corpus baseline; no neural model or downloads."""

    def __init__(self, *, alpha: float = 0.5):
        self.alpha = alpha
        self.class_counts: Counter[str] = Counter()
        self.feature_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.vocabulary: set[str] = set()
        self.training_source_ids: set[str] = set()

    def fit(self, records: Iterable[RevisionRecord], *, require_verified_license: bool = True) -> "MultinomialIntentModel":
        for record in records:
            if require_verified_license and not record.license_verified:
                raise ValueError(f"Refusing training record with unverified license: {record.record_id}")
            labels = record.canonical_labels
            if not labels:
                continue
            label = labels[0]
            self.training_source_ids.add(record.source_document_id)
            self.class_counts[label] += 1
            features = _features(record.original_text, record.revised_text)
            self.feature_counts[label].update(features)
            self.vocabulary.update(features)
        if not self.class_counts:
            raise ValueError("No labeled records are available for intent-model training")
        return self

    def predict_proba(self, original: str, revised: str) -> dict[str, float]:
        if not self.class_counts:
            raise ValueError("Intent model has not been fitted")
        features = _features(original, revised)
        total_records = sum(self.class_counts.values())
        vocab_size = max(1, len(self.vocabulary))
        logs: dict[str, float] = {}
        for label, class_count in self.class_counts.items():
            counts = self.feature_counts[label]
            total = sum(counts.values())
            score = math.log(class_count / total_records)
            for feature, frequency in features.items():
                if feature not in self.vocabulary:
                    continue
                score += frequency * math.log((counts[feature] + self.alpha) / (total + self.alpha * vocab_size))
            logs[label] = score
        pivot = max(logs.values())
        exp = {label: math.exp(value - pivot) for label, value in logs.items()}
        normalizer = sum(exp.values())
        return {label: value / normalizer for label, value in sorted(exp.items(), key=lambda item: item[1], reverse=True)}

    def predict(self, original: str, revised: str) -> tuple[str, float]:
        label, probability = next(iter(self.predict_proba(original, revised).items()))
        return label, probability

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "ateval-intent-nb-v1", "alpha": self.alpha, "class_counts": dict(self.class_counts), "feature_counts": {label: dict(counts) for label, counts in self.feature_counts.items()}, "vocabulary": sorted(self.vocabulary), "training_source_ids": sorted(self.training_source_ids)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MultinomialIntentModel":
        if data.get("schema") != "ateval-intent-nb-v1":
            raise ValueError("Unsupported intention model schema")
        model = cls(alpha=float(data["alpha"]))
        model.class_counts.update({str(key): int(value) for key, value in data["class_counts"].items()})
        model.feature_counts = defaultdict(Counter, {str(label): Counter({str(key): int(value) for key, value in counts.items()}) for label, counts in data["feature_counts"].items()})
        model.vocabulary = set(map(str, data["vocabulary"]))
        model.training_source_ids = set(map(str, data.get("training_source_ids", [])))
        return model

    def save(self, path: str | Path) -> None:
        target = Path(path)
        if target.exists():
            raise FileExistsError(f"Model output already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "MultinomialIntentModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
