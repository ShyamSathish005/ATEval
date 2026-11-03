"""Schema and validation for AI-text detection benchmarks and datasets.

Preserves original dataset class labels while mapping records to standard
benchmark tasks:
- Task A: Human versus AI text (binary: human vs pure AI, strictly excludes mixed)
- Task B: Mixed authorship (hybrid text: human + AI, AI + AI-refined, etc.)
- Task C: Academic-domain generalisation (in-domain academic vs cross-domain)
- Task D: Passage-level localisation (strictly requires verified span annotations)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class TaskKind(str, Enum):
    TASK_A_BINARY = "task_a_binary"
    TASK_B_MIXED = "task_b_mixed"
    TASK_C_DOMAIN = "task_c_domain"
    TASK_D_PASSAGE = "task_d_passage"


class AuthorshipClass(str, Enum):
    HUMAN = "human"
    AI = "ai"
    MIXED = "mixed"


@dataclass(frozen=True)
class SpanAnnotation:
    """Passage-level ground-truth span."""
    start_char: int
    end_char: int
    label: str
    source: str = "ground_truth"

    def validate(self, text_length: int) -> list[str]:
        errors = []
        if self.start_char < 0:
            errors.append(f"start_char ({self.start_char}) cannot be negative")
        if self.end_char > text_length:
            errors.append(f"end_char ({self.end_char}) exceeds text length ({text_length})")
        if self.start_char >= self.end_char:
            errors.append(f"start_char ({self.start_char}) must be strictly less than end_char ({self.end_char})")
        if not self.label.strip():
            errors.append("label must not be empty")
        return errors


@dataclass
class DetectionRecord:
    """Standardized record for detection benchmark tasks.
    
    Preserves original labels and provenance while enabling leakage-resistant
    splitting by prompt, document, author, domain, and model.
    """
    id: str
    text: str
    label: str  # "human", "ai", or "mixed"
    original_label: str  # verbatim label from original dataset
    source_dataset: str
    generator_model: str | None = None
    domain: str = "general"
    subdomain: str | None = None
    prompt: str | None = None
    document_id: str | None = None
    author_id: str | None = None
    has_span_labels: bool = False
    spans: list[SpanAnnotation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            # Deterministic hash ID based on source and content
            key = f"{self.source_dataset}:{self.original_label}:{self.text}"
            self.id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def validate(self) -> list[str]:
        errors = []
        if not self.text or not self.text.strip():
            errors.append("text must not be empty")
        if self.label not in {cls.value for cls in AuthorshipClass}:
            errors.append(f"label '{self.label}' must be one of: human, ai, mixed")
        if not self.original_label:
            errors.append("original_label must be preserved")
        if not self.source_dataset:
            errors.append("source_dataset must not be empty")
        if self.has_span_labels:
            if not self.spans:
                errors.append("has_span_labels is True but spans list is empty")
            for span in self.spans:
                errors.extend(span.validate(len(self.text)))
        elif self.spans:
            errors.append("spans provided but has_span_labels is False")
        return errors

    def word_count(self) -> int:
        return len(self.text.split())

    def length_group(self) -> str:
        words = self.word_count()
        if words < 100:
            return "<100"
        if words <= 200:
            return "100-200"
        if words <= 300:
            return "201-300"
        return ">300"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DetectionRecord:
        d = dict(data)
        if "spans" in d and d["spans"]:
            d["spans"] = [
                span if isinstance(span, SpanAnnotation) else SpanAnnotation(**span)
                for span in d["spans"]
            ]
        return cls(**d)


@dataclass
class DatasetManifest:
    """Auditable metadata and integrity record for an external dataset."""
    name: str
    version: str
    source: str
    doi: str | None
    licence: str
    citation: str
    download_url: str | None
    download_date: str
    sha256_hash: str
    file_size_bytes: int
    total_samples: int
    class_distribution: dict[str, int]
    transformations: list[str] = field(default_factory=list)
    qualification_status: str = "pending"
    qualification_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetManifest:
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> DatasetManifest:
        content = Path(path).read_text(encoding="utf-8")
        return cls.from_dict(json.loads(content))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")

