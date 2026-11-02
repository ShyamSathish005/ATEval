"""Small, dependency-free dataset record schema and validation helpers."""

from dataclasses import dataclass
from typing import Any, Mapping


REQUIRED_FIELDS = ("sample_id", "text", "label", "source_id", "dataset")
ALLOWED_LABELS = frozenset({"human", "machine", "mixed", "unknown"})


@dataclass(frozen=True)
class DatasetRecord:
    sample_id: str
    text: str
    label: str
    source_id: str
    dataset: str
    generator: str | None = None
    domain: str | None = None
    language: str | None = None
    split: str | None = None
    metadata: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "DatasetRecord":
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if missing:
            raise ValueError(f"missing required field(s): {', '.join(missing)}")
        for key in ("sample_id", "text", "source_id", "dataset"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise ValueError(f"{key} must be a non-empty string")
        if row["label"] not in ALLOWED_LABELS:
            raise ValueError(f"label must be one of: {', '.join(sorted(ALLOWED_LABELS))}")
        return cls(**{k: row.get(k) for k in cls.__dataclass_fields__})
