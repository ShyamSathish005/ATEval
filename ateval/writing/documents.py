"""Local text extraction for supported manuscript formats.

Extraction is read-only. No parser stores or rewrites its input. DOCX/PDF text
is an analysis projection and cannot be written back by this module.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".txt", ".tex", ".docx", ".pdf"}
MAX_DOCUMENT_BYTES = max(1, int(os.environ.get("ATEVAL_UPLOAD_LIMIT_BYTES", str(25 * 1024 * 1024))))


def extract_document(filename: str, content: bytes) -> dict[str, Any]:
    suffix = Path(filename).suffix.casefold()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Choose a .txt, .tex, .docx or .pdf document")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"Document exceeds the {MAX_DOCUMENT_BYTES}-byte local extraction limit")
    if suffix in {".txt", ".tex"}:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding") from exc
        extraction = "source text" if suffix == ".txt" else "raw LaTeX source (read-only inspection)"
    elif suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX support is optional. Install it with `python -m pip install -e '.[writing-docs]'`.") from exc
        try:
            doc = Document(io.BytesIO(content))
            blocks: list[str] = []
            for item in doc.iter_inner_content():
                if hasattr(item, "text"):
                    if item.text.strip():
                        blocks.append(item.text)
                elif hasattr(item, "rows"):
                    for row in item.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        if any(cells):
                            blocks.append("\t".join(cells))
            text = "\n\n".join(blocks)
        except Exception as exc:
            raise ValueError("Could not read this DOCX document") from exc
        extraction = "DOCX paragraph/table text projection (not a writable document mapping)"
    else:
        try:
            import pymupdf
        except ImportError as exc:
            raise RuntimeError("PDF support is optional. Install it with `python -m pip install -e '.[writing-docs]'`.") from exc
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
            pages = [page.get_text("text", sort=True).strip() for page in doc]
            nonempty = [page for page in pages if page]
            reliable_pages = sum(len(re.sub(r"\s", "", page)) >= 35 for page in pages)
            if not pages or not nonempty or reliable_pages / len(pages) < 0.8:
                raise ValueError("PDF text extraction is sparse or likely scanned. No OCR was run; provide a reliable text-layer PDF or source text.")
            text = "\n\n".join(f"[Page {index + 1}]\n{page}" for index, page in enumerate(pages) if page)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Could not reliably extract text from this PDF") from exc
        extraction = "PDF text-layer projection with page markers (not a writable document mapping)"
    if not text.strip():
        raise ValueError("No readable text was found in this document")
    return {
        "name": Path(filename).name,
        "format": suffix.lstrip("."),
        "text": text,
        "character_count": len(text),
        "extraction": extraction,
        "source_modified": False,
        "write_back_supported": False,
    }
