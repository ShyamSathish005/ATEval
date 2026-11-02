"""Blinded SCAR human-evaluation packet, annotation, and statistics utilities."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / "experiments" / "milestone4_4"
PACKET_PATH = EVAL_ROOT / "review_packet.jsonl"
ANNOTATIONS_PATH = EVAL_ROOT / "reviewer_annotations.jsonl"
KEY_PATH = EVAL_ROOT / "blind_key.json"
ANNOTATION_LABELS = {
    "NO_EDIT_REQUIRED", "GRAMMAR_IMPROVEMENT", "CLARITY_IMPROVEMENT",
    "REDUNDANCY_REMOVAL", "STRUCTURAL_IMPROVEMENT",
    "TECHNICAL_REVIEW_REQUIRED", "INSUFFICIENT_CONTEXT",
}
ASSESSMENTS = {"IMPROVED", "EQUIVALENT", "WORSE", "UNACCEPTABLE", "CANNOT_ASSESS"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _shuffle_candidates(item_id: str, candidates: dict[str, str | None], reviewer_id: str) -> list[dict[str, str]]:
    seed = int(hashlib.sha256(f"{item_id}:{reviewer_id}".encode()).hexdigest()[:16], 16)
    order = [name for name in candidates if name != "ORIGINAL"]
    random.Random(seed).shuffle(order)
    return [{"label": chr(ord("A") + index), "text": candidates[name]} for index, name in enumerate(order) if candidates[name]]


def build_packet() -> dict[str, Any]:
    source_path = ROOT / "reports/milestone4_2/scar_dev_comparison_predictions.jsonl"
    dev_rows = _read_jsonl(source_path)
    test_path = ROOT / "reports/milestone4_1/xtragpt_1_5b_q8_0_predictions.jsonl"
    test_rows = _read_jsonl(test_path)
    selected_dev = dev_rows
    selected_ids = {row["record_id"] for row in selected_dev}
    remaining = [row for row in test_rows if row["record_id"] not in selected_ids]
    random.Random(44).shuffle(remaining)
    necessity_rows = remaining[:100]
    items: list[dict[str, Any]] = []
    key: dict[str, dict[str, str]] = {}
    for row in selected_dev:
        item_id = f"m44-comparison-{_stable_id(row['record_id'])}"
        candidates = {
            "ORIGINAL": row["source"],
            "FULL_MODEL": row["full_passage_output"],
            "SCAR_CANDIDATE": row["scar_output"] if row["scar_review_decision"] == "ACCEPT_FOR_AUTHOR_REVIEW" else None,
            "HUMAN_REFERENCE": row["reference"],
        }
        items.append({
            "item_id": item_id,
            "kind": "comparison",
            "source_document_id": row["source_document_id"],
            "discipline": "academic writing",
            "section": "unknown",
            "original_text": row["source"],
            "paragraph_context": "",
            "candidate_count": sum(value is not None for value in candidates.values()),
            "candidate_ids_available": [name for name, value in candidates.items() if value is not None],
            "source_record_id": row["record_id"],
        })
        key[item_id] = candidates
    for row in necessity_rows:
        item_id = f"m44-necessity-{_stable_id(row['record_id'])}"
        items.append({
            "item_id": item_id,
            "kind": "necessity",
            "source_document_id": row["source_document_id"],
            "discipline": "academic writing",
            "section": "unknown",
            "original_text": row["source"],
            "paragraph_context": "",
            "candidate_count": 1,
            "candidate_ids_available": ["ORIGINAL"],
            "source_record_id": row["record_id"],
        })
        key[item_id] = {"ORIGINAL": row["source"]}
    return {
        "schema": "ateval-m44-blind-packet-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": 44,
        "items": items,
        "key": key,
        "limitations": [
            "The 30 comparison rows are diagnostic development examples, not an independent test set.",
            "The 100 necessity rows are new source-document-grouped samples, but no necessity labels are inferred.",
            "Paragraph context is empty for this packet because the frozen prediction artifacts do not contain full context.",
            "Human ratings are pending and must not be simulated.",
        ],
    }


def initialize_evaluation() -> dict[str, Any]:
    EVAL_ROOT.mkdir(parents=True, exist_ok=True)
    packet = build_packet()
    key = packet.pop("key")
    if PACKET_PATH.exists() or KEY_PATH.exists():
        raise FileExistsError("M4.4 evaluation packet already exists; refusing overwrite")
    PACKET_PATH.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in packet["items"]) + "\n", encoding="utf-8")
    KEY_PATH.write_text(json.dumps({"schema": "ateval-m44-blind-key-v1", "key": key}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ANNOTATIONS_PATH.touch()
    manifest = {
        **{key: value for key, value in packet.items() if key != "items"},
        "packet_path": str(PACKET_PATH.relative_to(ROOT)),
        "packet_sha256": hashlib.sha256(PACKET_PATH.read_bytes()).hexdigest(),
        "blind_key_path": str(KEY_PATH.relative_to(ROOT)),
        "blind_key_sha256": hashlib.sha256(KEY_PATH.read_bytes()).hexdigest(),
        "item_count": len(packet["items"]),
        "comparison_count": sum(item["kind"] == "comparison" for item in packet["items"]),
        "necessity_count": sum(item["kind"] == "necessity" for item in packet["items"]),
    }
    (EVAL_ROOT / "evaluation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def public_packet(reviewer_id: str) -> list[dict[str, Any]]:
    if not reviewer_id or len(reviewer_id) > 64:
        raise ValueError("reviewer_id must be a non-empty pseudonymous identifier")
    packet = _read_jsonl(PACKET_PATH)
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))["key"]
    public: list[dict[str, Any]] = []
    for item in packet:
        candidates = key[item["item_id"]]
        public.append({
            key: value for key, value in {
                **item,
                "candidate_ids_available": None,
                "candidates": _shuffle_candidates(item["item_id"], candidates, reviewer_id),
            }.items() if key != "candidate_ids_available"
        })
    return public


def validate_annotation(annotation: dict[str, Any]) -> None:
    required = {"item_id", "reviewer_id", "editing_necessity", "confidence", "candidate_assessments", "abstained"}
    missing = required - set(annotation)
    if missing:
        raise ValueError(f"annotation is missing fields: {sorted(missing)}")
    if not annotation["reviewer_id"] or len(str(annotation["reviewer_id"])) > 64:
        raise ValueError("reviewer_id must be pseudonymous and at most 64 characters")
    if annotation["editing_necessity"] not in ANNOTATION_LABELS:
        raise ValueError("invalid editing_necessity")
    if not isinstance(annotation["confidence"], int) or not 1 <= annotation["confidence"] <= 5:
        raise ValueError("confidence must be an integer from 1 to 5")
    if not isinstance(annotation["abstained"], bool):
        raise ValueError("abstained must be boolean")
    for candidate in annotation["candidate_assessments"]:
        if candidate.get("assessment") not in ASSESSMENTS:
            raise ValueError("invalid candidate assessment")
        for field in ("scientific_meaning", "numerical_accuracy", "technical_terminology", "causal_relationships", "qualifications", "limitations", "citation_integrity", "technical_correctness"):
            value = candidate.get(field)
            if value not in ASSESSMENTS:
                raise ValueError(f"invalid {field}")


def append_annotation(annotation: dict[str, Any]) -> None:
    validate_annotation(annotation)
    known = {item["item_id"] for item in _read_jsonl(PACKET_PATH)}
    if annotation["item_id"] not in known:
        raise ValueError("unknown evaluation item")
    existing = _read_jsonl(ANNOTATIONS_PATH)
    if any(item["item_id"] == annotation["item_id"] and item["reviewer_id"] == annotation["reviewer_id"] for item in existing):
        raise ValueError("duplicate annotation for this reviewer and item")
    record = {**annotation, "recorded_at": datetime.now(timezone.utc).isoformat()}
    with ANNOTATIONS_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def _weighted_kappa(left: list[int], right: list[int]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    categories = range(1, 6)
    observed = sum(1 - ((a - b) / 4) ** 2 for a, b in zip(left, right)) / len(left)
    expected = 0.0
    for a in categories:
        for b in categories:
            pa = left.count(a) / len(left)
            pb = right.count(b) / len(right)
            expected += pa * pb * (1 - ((a - b) / 4) ** 2)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def analyze_annotations() -> dict[str, Any]:
    rows = _read_jsonl(ANNOTATIONS_PATH)
    by_reviewer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_reviewer[row["reviewer_id"]].append(row)
        by_item[row["item_id"]].append(row)
    paired_confidence = []
    for item_rows in by_item.values():
        if len(item_rows) >= 2:
            paired_confidence.append((item_rows[0]["confidence"], item_rows[1]["confidence"]))
    kappas = [_weighted_kappa([a[0]], [a[1]]) for a in paired_confidence]
    return {
        "schema": "ateval-m44-annotation-analysis-v1",
        "annotation_count": len(rows),
        "reviewer_count": len(by_reviewer),
        "items_with_two_or_more_reviewers": sum(len(value) >= 2 for value in by_item.values()),
        "weighted_kappa_confidence_pairs": [value for value in kappas if value is not None],
        "preference_proportions": {},
        "confidence_intervals": "not_calculated_without reviewer annotations",
        "false_acceptance_rate": "not_calculated_without adjudicated human labels",
        "false_rejection_rate": "not_calculated_without adjudicated human labels",
        "status": "pending_human_annotations",
    }
