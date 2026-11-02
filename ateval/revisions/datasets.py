"""Offline adapters for IteraTeR and arXivEdits export files.

These adapters never download data. arXivEdits requires a separate
per-paper/per-version license manifest because the source repo records mixed
arXiv terms and the Hugging Face export omits those version-level terms.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from .alignment import extract_edit_spans
from .schema import EditSpan, RevisionRecord, validate_record
from .taxonomy import canonical_intent


@dataclass
class DatasetLoadResult:
    records: list[RevisionRecord]
    skipped: Counter[str]
    warnings: list[str]


def _read_rows(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return [dict(row) for row in csv.DictReader(stream)]
    raw = path.read_text(encoding="utf-8-sig")
    if suffix in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    if suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Official IteraTeR exports are newline-delimited JSON despite .json.
            try:
                data = [json.loads(line) for line in raw.splitlines() if line.strip()]
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON/JSONL export at line {exc.lineno}") from exc
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data, dict):
            # arXivEdits source exports can use paper-id -> revision records.
            rows = []
            for source_id, value in data.items():
                if isinstance(value, list):
                    rows.extend({"source_document_id": source_id, **item} for item in value if isinstance(item, dict))
                elif isinstance(value, dict):
                    rows.append({"source_document_id": source_id, **value})
            return rows
    raise ValueError("Dataset adapter accepts .json, .jsonl, .ndjson or .csv exports")


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return None


def _human_agreement(labels: Iterable[str]) -> float | None:
    values = [str(label) for label in labels if str(label).strip()]
    if len(values) < 2:
        return None
    counts = Counter(values)
    return max(counts.values()) / len(values)


def _embedded_context(row: dict[str, Any], before: str, intent: str | None) -> tuple[str, str]:
    tagged = str(row.get("before_sent_with_intent", ""))
    if "<S>" in tagged and "</S>" in tagged:
        left, rest = tagged.split("<S>", 1)
        target, right = rest.split("</S>", 1)
        target = target.strip()
        if target:
            return left.strip(), right.strip()
    # IteraTeR-HUMAN has an intent-prefixed input, not neighboring context.
    if intent:
        prefix = f"<{intent}>"
        if tagged.casefold().startswith(prefix.casefold()):
            tagged = tagged[len(prefix):].strip()
    return "", ""


def _record_from_sentence(row: dict[str, Any], dataset: str, split: str | None, source_license: str | None, license_verified: bool, row_index: int | None = None) -> RevisionRecord | None:
    before = str(row.get("before_sent", row.get("sentence-1", row.get("sentence_1", ""))) or "")
    after = str(row.get("after_sent", row.get("sentence-2", row.get("sentence_2", ""))) or "")
    if not before and not after:
        return None
    raw = row.get("labels", row.get("intentions", row.get("major_intent", "")))
    if isinstance(raw, list):
        raw_labels = tuple(str(label) for label in raw)
    else:
        raw_labels = (str(raw),) if str(raw).strip() else ()
    if not raw_labels:
        combinations = row.get("edits-combination-0", row.get("edits_combination_0"))
        if isinstance(combinations, str):
            try:
                combinations = json.loads(combinations)
            except json.JSONDecodeError:
                combinations = {}
        if isinstance(combinations, dict):
            raw_labels = tuple(str(item["intention"]) for item in combinations.values() if isinstance(item, dict) and item.get("intention"))
    mapped = tuple(dict.fromkeys(value for value in (canonical_intent(label) for label in raw_labels) if value))
    context_before, context_after = _embedded_context(row, before, raw_labels[0] if raw_labels else None)
    revision_stage = row.get("revision_depth", row.get("sentence-1-level", row.get("sentence_1_level")))
    return RevisionRecord(
        schema_version="revision-record-v1",
        record_id=str(row.get("record_id", row.get("id", f"{dataset}:{row.get('doc_id', row.get('arxiv-id', row.get('arxiv_id', 'unknown')))}:{revision_stage}:{row.get('sentence-pair-index', row_index if row_index is not None else 0)}"))),
        source_dataset=dataset,
        source_document_id=str(row.get("doc_id", row.get("arxiv-id", row.get("arxiv_id", row.get("source_document_id", "unknown"))))),
        revision_stage=revision_stage,
        split=split,
        original_text=before,
        revised_text=after,
        edit_spans=tuple(EditSpan(s["before_start"], s["before_end"], s["after_start"], s["after_end"], s["before"], s["after"], s["operation"], raw_labels[0] if raw_labels else None, mapped[0] if mapped else None) for s in extract_edit_spans(before, after)),
        raw_labels=raw_labels,
        canonical_labels=mapped,
        context_before=context_before,
        context_after=context_after,
        section_type=row.get("section_type"),
        annotation_confidence=_human_agreement(row.get("raw_intents", raw_labels)) or _float_or_none(row.get("confidence")),
        source_license=source_license or row.get("license"),
        license_verified=license_verified,
        metadata={"source_row": {key: value for key, value in row.items() if key not in {"before_sent", "after_sent", "sentence-1", "sentence-2", "sentence_1", "sentence_2", "before_revision", "after_revision"}}},
    )


def _record_from_document(row: dict[str, Any], split: str | None, source_license: str | None, license_verified: bool) -> list[RevisionRecord]:
    before = str(row.get("before_revision", "") or "")
    after = str(row.get("after_revision", "") or "")
    if not before and not after:
        return []
    doc_id = str(row.get("doc_id", row.get("source_document_id", "unknown")))
    stage = row.get("revision_depth")
    result = []
    for index, action in enumerate(row.get("edit_actions", []) or []):
        if not isinstance(action, dict):
            continue
        raw_label = action.get("major_intent")
        raw_intents = action.get("raw_intents", [])
        labels = tuple(str(label) for label in raw_intents if label) or ((str(raw_label),) if raw_label else ())
        canonical = canonical_intent(str(raw_label)) if raw_label else None
        start, end = action.get("start_char_pos"), action.get("end_char_pos")
        old_span, new_span = action.get("before"), action.get("after")
        after_start = after.find(str(new_span)) if new_span else None
        after_end = after_start + len(str(new_span)) if after_start is not None and after_start >= 0 else None
        span = EditSpan(start, end, after_start if after_start is not None and after_start >= 0 else None, after_end, old_span, new_span, str(action.get("type", "R")), str(raw_label) if raw_label else None, canonical, _human_agreement(raw_intents))
        context_start = max(0, int(start or 0) - 200)
        context_end = min(len(before), int(end or start or 0) + 200)
        record = RevisionRecord(
            schema_version="revision-record-v1",
            record_id=f"iterater:{doc_id}:{stage}:{index}",
            source_dataset="iterater-human-document",
            source_document_id=doc_id,
            revision_stage=stage,
            split=split,
            original_text=before,
            revised_text=after,
            edit_spans=(span,),
            raw_labels=labels,
            canonical_labels=(canonical,) if canonical else (),
            context_before=before[context_start:int(start or 0)],
            context_after=before[int(end or start or 0):context_end],
            section_type=row.get("section_type"),
            annotation_confidence=_human_agreement(raw_intents),
            source_license=source_license or row.get("license"),
            license_verified=license_verified,
            metadata={"domain": row.get("domain"), "operation": action.get("type"), "source_row_id": doc_id, "sents_char_pos": row.get("sents_char_pos")},
        )
        # Preserve even malformed corpus positions; audit surfaces an issue.
        result.append(record)
    return result


def _context_for_row(row: dict[str, Any], document: dict[str, Any]) -> tuple[str, str, str]:
    """Extract up to two neighboring source sentences from a paired document."""
    source = str(document.get("before_revision", "") or "")
    try:
        positions = sorted(set(int(value) for value in document.get("sents_char_pos", []) if 0 <= int(value) <= len(source)))
    except (TypeError, ValueError):
        positions = []
    spans = []
    for index, start in enumerate(positions):
        end = positions[index + 1] if index + 1 < len(positions) else len(source)
        piece = source[start:end]
        left, right = start + len(piece) - len(piece.lstrip()), start + len(piece.rstrip())
        if left < right:
            spans.append((left, right, source[left:right]))
    target = " ".join(str(row.get("before_sent", "")).split())
    index = next((i for i, (_, _, sentence) in enumerate(spans) if " ".join(sentence.split()) == target), None)
    if index is None and target:
        occurrence = source.find(str(row.get("before_sent", "")).strip())
        if occurrence >= 0:
            index = next((i for i, (left, right, _) in enumerate(spans) if left <= occurrence < right), None)
    if index is None:
        return "", "", source
    before = " ".join(sentence for _, _, sentence in spans[max(0, index - 2):index])
    after = " ".join(sentence for _, _, sentence in spans[index + 1:index + 3])
    return before, after, source


def load_iterater(path: str | Path, *, split: str | None = None, level: str = "sentence", variant: str = "human", source_license: str | None = None, license_verified: bool = False, document_context_path: str | Path | None = None) -> DatasetLoadResult:
    """Read user-provided IteraTeR JSON exports without network access."""
    rows = _read_rows(path)
    skipped: Counter[str] = Counter()
    records: list[RevisionRecord] = []
    source = f"iterater-{variant.casefold()}-{level.casefold()}"
    documents: dict[tuple[str, str], dict[str, Any]] = {}
    if document_context_path is not None and level == "sentence":
        for document in _read_rows(document_context_path):
            key = (str(document.get("doc_id", "unknown")), str(document.get("revision_depth", "unknown")))
            documents[key] = document
    for row_index, row in enumerate(rows):
        if level == "document":
            candidates = _record_from_document(row, split, source_license, license_verified)
        elif level == "sentence":
            record = _record_from_sentence(row, source, split, source_license, license_verified, row_index)
            document = documents.get((str(row.get("doc_id", "unknown")), str(row.get("revision_depth", "unknown"))))
            if record and document:
                before, after, full_context = _context_for_row(row, document)
                domain = str(document.get("domain", "")) or None
                record = replace(record, context_before=before, context_after=after, section_type="abstract" if domain == "arxiv" else domain, metadata={**record.metadata, "domain": domain, "document_context": full_context})
            candidates = [record] if record else []
        else:
            raise ValueError("level must be 'sentence' or 'document'")
        if not candidates:
            skipped["missing_source_or_revision"] += 1
            continue
        for record in candidates:
            issues = validate_record(record)
            if issues:
                skipped["invalid_record"] += 1
                continue
            records.append(record)
    warning = []
    if variant.casefold() == "full":
        warning.append("FULL labels are model-propagated and include confidence scores; keep them separate from manually annotated HUMAN labels.")
    if not license_verified:
        warning.append("License was not verified by the adapter; do not use these records for training until provenance terms are reviewed.")
    return DatasetLoadResult(records, skipped, warning)


def _field(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _whitespace_token_span(text: str, indices: Any) -> tuple[int, int, str] | None:
    if not isinstance(indices, (list, tuple)) or len(indices) != 2:
        return None
    try:
        first, last = int(indices[0]), int(indices[1])
    except (TypeError, ValueError):
        return None
    tokens = list(re.finditer(r"\S+", text))
    if first < 0 or last <= first or last > len(tokens):
        return None
    start, end = tokens[first].start(), tokens[last - 1].end()
    return start, end, text[start:end]


def load_arxivedits(path: str | Path, *, split: str | None, license_manifest: dict[str, Any] | None = None, permitted_licenses: set[str] | None = None) -> DatasetLoadResult:
    """Read an arXivEdits edit-export, requiring explicit version terms.

    The official arXivEdits repo lists per-paper version licenses; it has no
    repository-wide dataset grant. This function therefore abstains unless
    both versions have manifest entries and the caller explicitly permits
    each exact license identifier.
    """
    rows = _read_rows(path)
    manifest = license_manifest or {}
    permits = permitted_licenses or set()
    skipped: Counter[str] = Counter()
    records: list[RevisionRecord] = []
    for index, row in enumerate(rows):
        arxiv_id = str(_field(row, "arxiv-id", "arxiv_id", "paper_id", "source_document_id") or "")
        v1 = str(_field(row, "sentence-1-level", "sentence_1_level", "version_1", "source_version") or "")
        v2 = str(_field(row, "sentence-2-level", "sentence_2_level", "version_2", "target_version") or "")
        entry = manifest.get(arxiv_id, {})
        versions = entry.get("versions", entry) if isinstance(entry, dict) else {}
        license1 = versions.get(v1) or versions.get(f"v{v1}")
        license2 = versions.get(v2) or versions.get(f"v{v2}")
        if not license1 or not license2:
            skipped["version_license_missing"] += 1
            continue
        if license1 not in permits or license2 not in permits:
            skipped["license_not_permitted"] += 1
            continue
        record = _record_from_sentence(row, "arxivedits-edits", split, f"{license1}|{license2}", True)
        if record is None:
            skipped["missing_source_or_revision"] += 1
            continue
        edits = _field(row, "edits-combination-0", "edits_combination_0")
        if isinstance(edits, str):
            try:
                edits = json.loads(edits)
            except json.JSONDecodeError:
                edits = {}
        raw_intents = list(record.raw_labels)
        for combination in (edits or {}).values() if isinstance(edits, dict) else []:
            if isinstance(combination, dict) and combination.get("intention"):
                raw_intents.append(str(combination["intention"]))
        mapped = tuple(dict.fromkeys(value for value in (canonical_intent(label) for label in raw_intents) if value))
        manual_spans: list[EditSpan] = []
        op_names = {"substitute": "R", "insertion": "A", "deletion": "D"}
        for item in (edits or {}).values() if isinstance(edits, dict) else []:
            if not isinstance(item, dict):
                continue
            before_span = _whitespace_token_span(record.original_text, item.get("sentence-1-token-indices"))
            after_span = _whitespace_token_span(record.revised_text, item.get("sentence-2-token-indices"))
            raw_intent = str(item["intention"]) if item.get("intention") else None
            manual_spans.append(EditSpan(
                before_span[0] if before_span else None,
                before_span[1] if before_span else None,
                after_span[0] if after_span else None,
                after_span[1] if after_span else None,
                before_span[2] if before_span else None,
                after_span[2] if after_span else None,
                op_names.get(str(item.get("type", "")).casefold(), "R"),
                raw_intent,
                canonical_intent(raw_intent) if raw_intent else None,
            ))
        record = replace(
            record,
            record_id=f"arxivedits:{arxiv_id}:{v1}-{v2}:{index}",
            raw_labels=tuple(raw_intents),
            canonical_labels=mapped,
            edit_spans=tuple(manual_spans) or record.edit_spans,
            annotation_confidence=None,
            metadata={**record.metadata, "sentence_pair_index": _field(row, "sentence-pair-index", "sentence_pair_index"), "difficulty": _field(row, "easy-or-hard", "easy_or_hard"), "source_version": v1, "target_version": v2, "edit_combinations": edits},
        )
        if not validate_record(record):
            records.append(record)
        else:
            skipped["invalid_record"] += 1
    warnings = []
    if not manifest:
        warnings.append("No version-level license manifest supplied; all arXivEdits records are withheld.")
    return DatasetLoadResult(records, skipped, warnings)


def split_leakage(source_ids_by_split: dict[str, Iterable[str]]) -> dict[str, Any]:
    """Report source-document overlap; train/test leakage is a hard failure."""
    normalized = {name: set(map(str, ids)) for name, ids in source_ids_by_split.items()}
    overlaps = {}
    names = sorted(normalized)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            shared = sorted(normalized[left] & normalized[right])
            if shared:
                overlaps[f"{left}:{right}"] = shared
    return {"leakage_free": not overlaps, "overlaps": overlaps, "source_counts": {name: len(ids) for name, ids in normalized.items()}}
