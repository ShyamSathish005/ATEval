"""Source-preserving reviewed manuscript exports."""

from __future__ import annotations

import html
import io
import json
import posixpath
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .documents import DocumentBundle, import_manuscript
from ..revisions.protected_content import protect_content
from ..revisions.scar import compare_claim_cues


def sanitize_export_filename(filename: str | None, *, suffix: str, fallback_stem: str = "manuscript-reviewed") -> str:
    """Return a safe basename without control characters, quotes, or path separators."""
    raw = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(
        ch for ch in raw
        if ch not in {'"', "'", ";", "/", "\\", "\r", "\n", "\x00"} and unicodedata.category(ch)[0] != "C"
    ).strip()
    stem = Path(cleaned).stem if cleaned else ""
    stem = re.sub(r"\s+", "_", stem).strip("._-")[:120]
    if not stem:
        stem = fallback_stem
    safe_suffix = suffix if suffix.startswith((".", "-")) else f".{suffix}"
    return f"{stem}{safe_suffix}"


def build_content_disposition(filename: str, *, fallback_stem: str = "manuscript-reviewed") -> str:
    """Build an RFC 6266 / RFC 5987 compliant Content-Disposition attachment header."""
    cleaned = "".join(
        ch for ch in filename
        if ch not in {'"', "'", ";", "/", "\\", "\r", "\n", "\x00"} and unicodedata.category(ch)[0] != "C"
    ).strip() or f"{fallback_stem}.txt"
    ext = Path(cleaned).suffix or ".txt"
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(cleaned).stem).strip("._-")[:120] or fallback_stem
    ascii_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext)[:16] or ".txt"
    ascii_name = f"{ascii_stem}{ascii_ext}"
    encoded_utf8 = quote(cleaned.encode("utf-8"), safe="-_.~")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_utf8}"


def export_html_report(report: dict[str, Any]) -> tuple[bytes, str, str]:
    """Render a standalone, script-free HTML analysis report for attachment delivery."""
    doc = report.get("document") or {}
    cov = report.get("coverage") or {}
    summary = report.get("detector_summary") or {}
    profile = report.get("descriptive_writing_profile") or {}
    counts = profile.get("counts") or {}
    sentence_stats = profile.get("sentence") or {}
    lexical_stats = profile.get("lexical") or {}
    def esc(value: Any) -> str:
        return html.escape(str(value if value is not None else ""), quote=True)
    doc_name = esc(doc.get("name", "manuscript"))
    sections_html = "".join(f"<li>{esc(sec.get('title', 'Section'))}</li>" for sec in (doc.get("sections") or []))
    methods_html = "".join(
        f"<tr><td>{esc(m.get('detector_name'))}</td><td>{esc(m.get('detector_version') or 'not installed')}</td>"
        f"<td>{esc(m.get('implementation_status'))}</td><td>{esc(m.get('calibration_status'))}</td>"
        f"<td>{esc(m.get('uncertainty'))}</td><td>{esc(m.get('methodology'))}</td></tr>"
        for m in (report.get("detector_methods") or [])
    )
    passages_html = "".join(
        f"<article><h3>Passage {esc(p.get('sentence_index'))} · {esc(p.get('section'))}</h3>"
        f"<p>{esc(p.get('text'))}</p></article>"
        for p in (report.get("passages") or [])
    )
    limits_html = "".join(f"<li>{esc(limit)}</li>" for limit in (report.get("limitations") or []))
    csp = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'"
    document_html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<meta http-equiv=\"Content-Security-Policy\" content=\"{csp}\">"
        f"<title>ATEval manuscript report · {doc_name}</title>"
        "<style>body{font:14px/1.6 Arial,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#18263a}"
        "h1,h2{color:#172f58}.warning{padding:16px;background:#fff4df;border:1px solid #ead2a6;border-radius:10px}"
        "table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}"
        "article{border-bottom:1px solid #ddd;padding:12px 0}</style></head><body>"
        f"<h1>Manuscript Intelligence report</h1><p>{doc_name} · {esc(report.get('generated_at'))} · ID {esc(doc.get('document_id'))}</p>"
        f"<div class=\"warning\">{esc(summary.get('warning'))}</div>"
        f"<h2>Summary and coverage</h2><p>{esc(doc.get('words_in_prose_projection', 0))} words · "
        f"{esc(doc.get('sentence_count', 0))} passages · {esc(cov.get('editable_passage_count', 0))} editable passages.</p>"
        f"<h3>Sections</h3><ul>{sections_html}</ul>"
        f"<h2>Descriptive writing profile (not an authorship detector)</h2>"
        f"<p>{esc(counts.get('words', 0))} words · {esc(counts.get('sentences', 0))} sentences · "
        f"mean sentence length {esc(sentence_stats.get('mean_words') or 'not available')} · "
        f"length-sensitive TTR {esc(lexical_stats.get('type_token_ratio_length_sensitive') or 'not available')}.</p>"
        f"<h2>Independent method-specific results</h2><p>{esc(summary.get('interpretation'))}</p>"
        f"<table><thead><tr><th>Detector</th><th>Version</th><th>Status</th><th>Calibration</th><th>Uncertainty</th><th>Methodology</th></tr></thead>"
        f"<tbody>{methods_html}</tbody></table>"
        f"<h2>Passage-level status</h2>{passages_html}"
        f"<h2>Limitations</h2><ul>{limits_html}</ul></body></html>"
    )
    out_name = sanitize_export_filename(str(doc.get("name", "manuscript")), suffix="-analysis.html", fallback_stem="manuscript")
    return document_html.encode("utf-8"), "text/html; charset=utf-8", out_name


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
            out = changed.get(bundle.root_file or bundle.name, content)
            extension = ".txt" if bundle.format == "txt" else ".tex"
            return out, "text/plain; charset=utf-8", sanitize_export_filename(filename, suffix=f"-reviewed{extension}")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:
            for member_path, raw_bytes in bundle.files.items():
                data = changed.get(member_path, raw_bytes)
                target_zip.writestr(member_path, data)
        return output.getvalue(), "application/zip", sanitize_export_filename(filename, suffix="-reviewed.zip")

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
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", sanitize_export_filename(filename, suffix="-reviewed.docx")

    raise ValueError("This manuscript format does not have a source-preserving export implementation")
