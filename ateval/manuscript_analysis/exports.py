"""Source-preserving reviewed manuscript exports."""

from __future__ import annotations

import io
import json
import posixpath
import zipfile
from pathlib import Path
from typing import Any

from .documents import DocumentBundle, import_manuscript
from ..revisions.protected_content import protect_content
from ..revisions.scar import compare_claim_cues


def _validate_patch(source: str, replacement: str, protected_terms: list[str] | tuple[str, ...] = ()) -> None:
    before = protect_content(source, tuple(protected_terms))
    after = protect_content(replacement, tuple(protected_terms))
    if [item.original for item in before.mapping] != [item.original for item in after.mapping]:
        raise ValueError("Accepted edit changes protected numbers, citations, equations, identifiers, URLs, code, or terminology")
    if compare_claim_cues(source, replacement).status == "cue_mismatch":
        raise ValueError("Accepted edit changes a claim-sensitive cue; revise or obtain expert review before export")


def _check_ranges(text: str, patches: list[dict[str, Any]], *, locator: str) -> list[tuple[int, int, str]]:
    ranges = []
    for patch in patches:
        try:
            start, end = int(patch["start"]), int(patch["end"])
            source, replacement = str(patch["source_text"]), str(patch["replacement"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Each accepted edit needs a source range, exact source text, and replacement") from exc
        if start < 0 or end <= start or end > len(text) or text[start:end] != source:
            raise ValueError("An accepted edit no longer matches its original source range")
        ranges.append((start, end, replacement))
    ordered = sorted(ranges)
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] < previous[1]:
            raise ValueError(f"Accepted edits overlap in {locator}; review them separately")
    return ranges


def _apply_ranges(text: str, ranges: list[tuple[int, int, str]]) -> str:
    output = text
    for start, end, replacement in sorted(ranges, reverse=True):
        output = output[:start] + replacement + output[end:]
    return output


def export_reviewed_manuscript(filename: str, content: bytes, patches: list[dict[str, Any]]) -> tuple[bytes, str, str]:
    bundle = import_manuscript(filename, content)
    if not bundle.write_back_supported or bundle.format == "pdf":
        raise ValueError("PDF is read-only. Export the source document or choose an explicit PDF conversion workflow.")
    if not patches:
        raise ValueError("Select at least one individually accepted edit before exporting a revised manuscript")

    if bundle.format in {"txt", "tex", "zip"}:
        by_path: dict[str, list[dict[str, Any]]] = {}
        for patch in patches:
            source_map = patch.get("source_map") or {}
            path = str(source_map.get("path", ""))
            if path not in bundle.source_texts:
                raise ValueError("An accepted edit points outside the imported manuscript source files")
            if source_map.get("editable") is not True:
                raise ValueError("An accepted edit has no exact editable source mapping")
            start, end = int(source_map.get("start", -1)), int(source_map.get("end", -1))
            source = bundle.source_texts[path]
            if start < 0 or end > len(source) or end <= start or source[start:end] != patch.get("source_text"):
                raise ValueError("An accepted edit no longer matches its original source range")
            _validate_patch(str(patch["source_text"]), str(patch["replacement"]), patch.get("protected_terms", ()))
            item = {**patch, "start": source_map.get("start"), "end": source_map.get("end")}
            by_path.setdefault(path, []).append(item)
        changed: dict[str, bytes] = {}
        for path, items in by_path.items():
            source = bundle.source_texts[path]
            changed[path] = _apply_ranges(source, _check_ranges(source, items, locator=path)).encode("utf-8")
        if bundle.format in {"txt", "tex"}:
            out = changed.get(bundle.root_file or filename, content)
            extension = ".txt" if bundle.format == "txt" else ".tex"
            return out, "text/plain; charset=utf-8", f"{Path(filename).stem}-reviewed{extension}"
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(content), "r") as source_zip, zipfile.ZipFile(output, "w") as target_zip:
            for info in source_zip.infolist():
                if info.is_dir():
                    target_zip.writestr(info, b"")
                    continue
                data = changed.get(info.filename, source_zip.read(info.filename))
                target_zip.writestr(info, data)
        return output.getvalue(), "application/zip", f"{Path(filename).stem}-reviewed.zip"

    if bundle.format == "docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX export needs python-docx; install the optional writing-docs extra") from exc
        document = Document(io.BytesIO(content))
        groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for patch in patches:
            source_map = patch.get("source_map") or {}
            if source_map.get("editable") is not True or source_map.get("block") != "body":
                raise ValueError("This DOCX passage crosses a run or is outside editable body paragraphs")
            key = (int(source_map["paragraph"]), int(source_map["run"]))
            if key[0] >= len(document.paragraphs) or key[1] >= len(document.paragraphs[key[0]].runs):
                raise ValueError("The DOCX source locator is no longer valid")
            groups.setdefault(key, []).append({
                "start": source_map.get("start"), "end": source_map.get("end"),
                "source_text": patch.get("source_text"), "replacement": patch.get("replacement"),
            })
            _validate_patch(str(patch.get("source_text", "")), str(patch.get("replacement", "")), patch.get("protected_terms", ()))
        for (paragraph_index, run_index), items in groups.items():
            run = document.paragraphs[paragraph_index].runs[run_index]
            run.text = _apply_ranges(run.text, _check_ranges(run.text, items, locator=f"paragraph {paragraph_index}, run {run_index}"))
        output = io.BytesIO()
        document.save(output)
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{Path(filename).stem}-reviewed.docx"

    raise ValueError("This manuscript format does not have a source-preserving export implementation")
