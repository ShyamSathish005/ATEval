"""Create immutable document-grouped IteraTeR-HUMAN partitions and manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "processed" / "iterater_human_grouped_v1"
MANIFESTS = ROOT / "data" / "manifests"
SPLITS = ("train", "dev", "test")
LICENSE = "Apache-2.0 (dataset card published by author account wanyu)"
SENT_REVISION = "7a570cd"
DOC_REVISION = "ec416e7"
SALT = "ateval-iterater-human-doc-group-v1"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _norm(text: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text or "")).casefold().split())


def _partition(document_id: str) -> str:
    bucket = int(hashlib.sha256(f"{SALT}:{document_id}".encode()).hexdigest()[:8], 16) % 100
    return "train" if bucket < 70 else "dev" if bucket < 85 else "test"


def _record_id(row: dict[str, Any]) -> str:
    key = "\x1f".join((str(row.get("doc_id", "")), str(row.get("revision_depth", "")), _norm(row.get("before_sent")), _norm(row.get("after_sent")), str(row.get("labels", "")).casefold()))
    return "iterater-human:" + hashlib.sha256(key.encode()).hexdigest()[:24]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit_records(rows: list[dict[str, Any]], docs: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts = Counter(str(row.get("labels", "")) for row in rows)
    doc_ids = {str(row.get("doc_id", "")) for row in rows}
    contexts = {(str(row.get("doc_id", "")), str(row.get("revision_depth", ""))) for row in docs}
    with_context = sum((str(row.get("doc_id", "")), str(row.get("revision_depth", ""))) in contexts for row in rows)
    signature_counts = Counter((_norm(row.get("before_sent")), _norm(row.get("after_sent")), str(row.get("labels", "")).casefold()) for row in rows)
    blank_after = sum(not str(row.get("after_sent", "")).strip() for row in rows)
    return {
        "sentence_records": len(rows), "document_records": len(docs), "source_documents": len(doc_ids),
        "raw_label_counts": dict(sorted(label_counts.items())),
        "empty_before": sum(not str(row.get("before_sent", "")).strip() for row in rows),
        "empty_after_valid_deletion_candidates": blank_after,
        "missing_label": sum(not str(row.get("labels", "")).strip() for row in rows),
        "no_op_pairs": sum(_norm(row.get("before_sent")) == _norm(row.get("after_sent")) for row in rows),
        "exact_pair_label_duplicate_groups": sum(count > 1 for count in signature_counts.values()),
        "exact_pair_label_duplicate_excess": sum(count - 1 for count in signature_counts.values() if count > 1),
        "document_context_match_rate": with_context / len(rows) if rows else None,
        "domains": dict(sorted(Counter(str(row.get("domain", "unknown")) for row in docs).items())),
        "revision_depth_counts": dict(sorted(Counter(str(row.get("revision_depth", "unknown")) for row in rows).items())),
    }


def prepare() -> dict[str, Any]:
    destinations = [OUTPUT / f"sentence_{split}.jsonl" for split in SPLITS]
    destinations += [OUTPUT / f"document_{split}.jsonl" for split in SPLITS]
    destinations += [MANIFESTS / f"revision_{name}_manifest.json" for name in ("training", "validation", "test")]
    destinations += [ROOT / "docs" / "dataset_ingestion_report.md", ROOT / "docs" / "dataset_quality_report.md"]
    existing = [path for path in destinations if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite immutable outputs: {existing[0]}")

    sentence_rows: list[dict[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    raw_hashes = {}
    for upstream_split in SPLITS:
        sent_path = RAW / "iterater_human_sent" / f"{upstream_split}.json"
        doc_path = RAW / "iterater_human_doc" / f"{upstream_split}.json"
        raw_hashes[str(sent_path.relative_to(ROOT))] = _hash(sent_path)
        raw_hashes[str(doc_path.relative_to(ROOT))] = _hash(doc_path)
        for row in _jsonl(sent_path):
            sentence_rows.append({**row, "source_upstream_split": upstream_split})
        for row in _jsonl(doc_path):
            document_rows.append({**row, "source_upstream_split": upstream_split})

    upstream_docs: dict[str, set[str]] = {split: set() for split in SPLITS}
    for row in sentence_rows:
        upstream_docs[str(row["source_upstream_split"])].add(str(row.get("doc_id", "")))
    upstream_overlaps = {}
    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1:]:
            shared = sorted(upstream_docs[left] & upstream_docs[right])
            if shared:
                upstream_overlaps[f"{left}:{right}"] = {"count": len(shared), "document_ids": shared}

    owners: dict[tuple[str, str, str, str, str], tuple[str, int]] = {}
    deduped_sentences: list[dict[str, Any]] = []
    duplicate_count = 0
    for index, row in enumerate(sentence_rows):
        signature = (str(row.get("doc_id", "")), str(row.get("revision_depth", "")), _norm(row.get("before_sent")), _norm(row.get("after_sent")), str(row.get("labels", "")).casefold())
        if signature in owners:
            duplicate_count += 1
            continue
        owners[signature] = (str(row["source_upstream_split"]), index)
        prepared = dict(row)
        prepared["record_id"] = _record_id(row)
        prepared["ateval_split"] = _partition(str(row.get("doc_id", "")))
        deduped_sentences.append(prepared)

    doc_signatures = set()
    prepared_documents = []
    duplicate_docs = 0
    for row in document_rows:
        signature = (str(row.get("doc_id", "")), str(row.get("revision_depth", "")), _norm(row.get("before_revision")), _norm(row.get("after_revision")))
        if signature in doc_signatures:
            duplicate_docs += 1
            continue
        doc_signatures.add(signature)
        prepared = dict(row)
        prepared["ateval_split"] = _partition(str(row.get("doc_id", "")))
        prepared_documents.append(prepared)

    OUTPUT.mkdir(parents=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    report = {"prepared_at": date.today().isoformat(), "license": LICENSE, "source_hashes": raw_hashes, "upstream_document_overlaps": upstream_overlaps, "deduplication": {"exact_sentence_pair_label_duplicates_removed": duplicate_count, "exact_document_revision_duplicates_removed": duplicate_docs}, "splits": {}}
    names = {"train": "training", "dev": "validation", "test": "test"}
    for split in SPLITS:
        sent_rows = [row for row in deduped_sentences if row["ateval_split"] == split]
        doc_rows = [row for row in prepared_documents if row["ateval_split"] == split]
        sentence_path, document_path = OUTPUT / f"sentence_{split}.jsonl", OUTPUT / f"document_{split}.jsonl"
        sentence_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sent_rows), encoding="utf-8")
        document_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in doc_rows), encoding="utf-8")
        record_ids = [row["record_id"] for row in sent_rows]
        doc_ids = sorted({str(row.get("doc_id", "")) for row in sent_rows})
        manifest = {
            "schema": "ateval-revision-data-manifest-v1", "created": date.today().isoformat(),
            "dataset": "IteraTeR-HUMAN", "task": "sentence-level revision intention and generation",
            "split": split, "grouping": "source_document_id; stable sha256 assignment, 70/15/15", "split_seed": SALT,
            "source": {
                "sentence_dataset": "https://huggingface.co/datasets/wanyu/IteraTeR_human_sent",
                "document_dataset": "https://huggingface.co/datasets/wanyu/IteraTeR_human_doc",
                "sentence_file_revision": SENT_REVISION, "document_file_revision": DOC_REVISION,
                "license": LICENSE,
                "review": "The author account's public dataset card declares Apache-2.0 for the HUMAN split; the upstream data README separately restricts IteraTeR Plus and v2. Those corpora are not used here.",
            },
            "raw_input_sha256": raw_hashes,
            "processed_sentence_file": str(sentence_path.relative_to(ROOT)), "processed_sentence_sha256": _hash(sentence_path),
            "processed_document_file": str(document_path.relative_to(ROOT)), "processed_document_sha256": _hash(document_path),
            "row_count": len(sent_rows), "document_count": len(doc_ids),
            "source_document_ids_sha256": hashlib.sha256("\n".join(doc_ids).encode()).hexdigest(),
            "record_ids": record_ids,
        }
        manifest_path = MANIFESTS / f"revision_{names[split]}_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["splits"][split] = {**_audit_records(sent_rows, doc_rows), "sentence_sha256": manifest["processed_sentence_sha256"], "document_sha256": manifest["processed_document_sha256"]}
    (MANIFESTS / "revision_dataset_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = prepare()
    print(json.dumps({"split_counts": {split: values["sentence_records"] for split, values in report["splits"].items()}, "upstream_document_overlap_pairs": {key: value["count"] for key, value in report["upstream_document_overlaps"].items()}, "manifests": str(MANIFESTS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
