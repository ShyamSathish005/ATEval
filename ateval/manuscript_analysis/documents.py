"""Safe manuscript import and source-location mapping.

PDF is read-only. DOCX suggestions are editable only when a passage lies
inside one text run. LaTeX output is a prose projection with raw source spans;
unsupported macros and binary elements are explicitly reported.
"""

from __future__ import annotations

import hashlib
import io
import posixpath
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ..writing.documents import MAX_DOCUMENT_BYTES, extract_document

MAX_PROJECT_FILES = 2000
MAX_PROJECT_EXPANDED_BYTES = 100 * 1024 * 1024
SUPPORTED = {".txt", ".tex", ".zip", ".docx", ".pdf"}
MATH_OR_NONPROSE_ENVS = {"equation", "equation*", "align", "align*", "gather", "gather*", "multline", "multline*", "math", "displaymath", "verbatim", "verbatim*", "lstlisting", "minted", "tikzpicture", "figure", "figure*", "table", "table*", "algorithm"}
DROP_COMMANDS = {"cite", "citep", "citet", "parencite", "textcite", "autocite", "ref", "eqref", "cref", "Cref", "label", "bibitem", "bibliography", "addbibresource", "url", "includegraphics", "bibliographystyle", "documentclass", "usepackage", "newcommand", "renewcommand", "providecommand", "def", "newenvironment"}
TEXT_COMMANDS = {"section", "subsection", "subsubsection", "chapter", "part", "paragraph", "subparagraph", "title", "author", "caption", "textbf", "textit", "emph", "underline", "textrm", "textsf", "texttt", "text", "footnote", "thanks", "mbox"}
INCLUDE_COMMANDS = {"input", "include", "subfile"}
KNOWN_COMMANDS = TEXT_COMMANDS | DROP_COMMANDS | INCLUDE_COMMANDS | {"begin", "end", "maketitle", "item", "par", "newline", "newpage", "centering", "small", "large", "Large", "footnotesize", "textcolor", "color", "hspace", "vspace", "quad", "qquad", "ldots", "dots", "LaTeX", "TeX", "today", "thanks", "and", "or", "author", "date", "maketitle", "appendix", "clearpage", "pagebreak", "linebreak", "noindent", "label", "definecolor", "setlength", "setcounter", "addcontentsline", "phantomsection", "footnotemark", "footnotetext", "protect", "slash", "%", "_", "&", "#", "$", "{", "}"}
COMMAND_RE = re.compile(r"\\([A-Za-z@]+\*?)")
INCLUDE_RE = re.compile(r"\s*\{([^{}]+)\}")
SECTION_BREAK_RE = re.compile(r"\\(?:part|chapter|section|subsection|subsubsection)\*?")


@dataclass(frozen=True)
class SourcePointer:
    path: str
    offset: int | None = None
    paragraph: int | None = None
    run: int | None = None
    run_offset: int | None = None
    page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}


@dataclass
class DocumentBundle:
    name: str
    format: str
    root_file: str | None
    files: dict[str, bytes]
    source_texts: dict[str, str]
    projection: str
    pointers: list[SourcePointer | None]
    unsupported: list[dict[str, Any]]
    section_markers: list[dict[str, Any]]
    write_back_supported: bool
    extraction: str
    source_sha256: str


def _decode(path: str, content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"LaTeX/text source {path} must use UTF-8 encoding") from exc


def _tex_refs(content: str) -> set[str]:
    refs = set()
    for match in re.finditer(r"\\(?:input|include|subfile)\s*\{([^{}]+)\}", content):
        target = match.group(1).strip()
        target = target if Path(target).suffix else target + ".tex"
        refs.add(posixpath.normpath(target))
    return refs


def _zip_files(content: bytes) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("The LaTeX project ZIP is malformed") from exc
    infos = [item for item in archive.infolist() if not item.is_dir()]
    if len(infos) > MAX_PROJECT_FILES:
        raise ValueError(f"LaTeX project ZIP exceeds the {MAX_PROJECT_FILES}-file limit")
    total = sum(item.file_size for item in infos)
    if total > MAX_PROJECT_EXPANDED_BYTES:
        raise ValueError("LaTeX project ZIP expands beyond the 100 MiB safety limit")
    files: dict[str, bytes] = {}
    for info in infos:
        if "\\" in info.filename:
            raise ValueError("LaTeX project ZIP contains an unsafe file path")
        windows_path = PureWindowsPath(info.filename)
        if windows_path.is_absolute() or windows_path.drive or ".." in windows_path.parts:
            raise ValueError("LaTeX project ZIP contains an unsafe file path")
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("LaTeX project ZIP contains an unsafe file path")
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError("LaTeX project ZIP may not contain symbolic links")
        normalized = path.as_posix()
        if normalized in files:
            raise ValueError(f"LaTeX project ZIP contains a duplicate path: {normalized}")
        files[normalized] = archive.read(info)
    return files


def _choose_root(sources: dict[str, str]) -> str:
    tex_paths = sorted(path for path in sources if path.casefold().endswith(".tex"))
    if not tex_paths:
        raise ValueError("LaTeX project ZIP contains no .tex files")
    referenced = set()
    for path, text in sources.items():
        parent = posixpath.dirname(path)
        referenced.update(posixpath.normpath(posixpath.join(parent, item)) for item in _tex_refs(text))
    roots = [path for path in tex_paths if path not in referenced]
    if len(roots) == 1:
        return roots[0]
    named = [path for path in roots if PurePosixPath(path).name.casefold() in {"main.tex", "manuscript.tex", "paper.tex", "root.tex"}]
    if len(named) == 1:
        return named[0]
    raise ValueError("Could not identify a unique LaTeX root file; include one unambiguous main/manuscript/paper.tex")


def _balanced_group(text: str, start: int) -> int | None:
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if char == "\\" and not escaped:
            escaped = True
            continue
        if char == "{" and not escaped:
            depth += 1
        elif char == "}" and not escaped:
            depth -= 1
            if depth == 0:
                return index + 1
        escaped = False
    return None


def _skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _tex_projection(root: str, sources: dict[str, str]) -> tuple[str, list[SourcePointer | None], list[dict[str, Any]], list[dict[str, Any]]]:
    unsupported: list[dict[str, Any]] = []
    section_markers: list[dict[str, Any]] = []
    active: list[str] = []
    custom_definitions = set()
    for value in sources.values():
        custom_definitions.update(re.findall(r"\\(?:newcommand|renewcommand|providecommand)\*?\s*\{\\([A-Za-z@]+)", value))
        custom_definitions.update(re.findall(r"\\def\s*\\([A-Za-z@]+)", value))
    out: list[str] = []
    pointers: list[SourcePointer | None] = []
    math_delimiters = {"\\[": "\\]", "\\(": "\\)", "$$": "$$", "$": "$"}

    def append_text(value: str, path: str, offsets: list[int] | None = None) -> None:
        out.extend(value)
        if offsets is None:
            pointers.extend(SourcePointer(path, offset=None) for _ in value)
        else:
            pointers.extend(SourcePointer(path, offset=offset) for offset in offsets)

    def render(path: str) -> None:
        if path in active:
            unsupported.append({"path": path, "kind": "include_cycle", "detail": "Recursive LaTeX include was not expanded."})
            return
        if path not in sources:
            unsupported.append({"path": path, "kind": "missing_include", "detail": "Included source file was not found in the selected project."})
            return
        active.append(path)
        text = sources[path]
        index = 0
        while index < len(text):
            # Ignore TeX comments while retaining line boundaries and positions.
            if text[index] == "%" and (index == 0 or text[index - 1] != "\\"):
                end = text.find("\n", index)
                if end < 0:
                    index = len(text)
                    continue
                append_text("\n", path, [end])
                index = end + 1
                continue
            env_start = re.match(r"\\begin\{([^{}]+)\}", text[index:])
            if env_start and env_start.group(1) in MATH_OR_NONPROSE_ENVS:
                env = env_start.group(1)
                opening_end = index + env_start.end()
                token = re.compile(rf"\\(?:begin|end)\{{{re.escape(env)}\}}")
                depth = 1
                cursor = opening_end
                while depth and (match := token.search(text, cursor)):
                    if match.group(0).startswith(r"\begin"):
                        depth += 1
                    else:
                        depth -= 1
                    cursor = match.end()
                finish = cursor if depth == 0 else len(text)
                unsupported.append({"path": path, "kind": "excluded_latex_environment", "environment": env, "start": index, "end": finish, "detail": "Equation, code, figure, table, or algorithm environment is preserved but excluded from prose analysis."})
                append_text("\n", path, [index])
                index = finish
                continue
            if text.startswith(("\\[", "\\(", "$$"), index) or text[index] == "$":
                delimiter = next((item for item in ("\\[", "\\(", "$$", "$") if text.startswith(item, index)), None)
                if delimiter:
                    closing = math_delimiters[delimiter]
                    end = text.find(closing, index + len(delimiter))
                    finish = len(text) if end < 0 else end + len(closing)
                    unsupported.append({"path": path, "kind": "excluded_math", "start": index, "end": finish, "detail": "Mathematical expression is preserved but excluded from prose analysis."})
                    append_text(" ", path, [index])
                    index = finish
                    continue
            if text[index] == "\\":
                command = COMMAND_RE.match(text, index)
                if command:
                    name = command.group(1).rstrip("*")
                    after = _skip_space(text, command.end())
                    if name in INCLUDE_COMMANDS:
                        group_end = _balanced_group(text, after)
                        if group_end is None:
                            unsupported.append({"path": path, "kind": "malformed_include", "start": index, "detail": f"Malformed \\{name} command."})
                        else:
                            target = text[after + 1:group_end - 1].strip()
                            target = target if Path(target).suffix else target + ".tex"
                            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
                            if target.startswith("../") or target == "..":
                                unsupported.append({"path": path, "kind": "unsafe_include", "start": index, "detail": "Include path escapes the project root."})
                            else:
                                append_text("\n", path, [index])
                                render(target)
                                append_text("\n", path, [group_end - 1])
                        index = group_end if group_end is not None else command.end()
                        continue
                    if name in {"begin", "end"}:
                        group_end = _balanced_group(text, after)
                        index = group_end if group_end is not None else command.end()
                        continue
                    if name in {"part", "chapter", "section", "subsection", "subsubsection"}:
                        title_start = after
                        if title_start < len(text) and text[title_start] == "[":
                            close = text.find("]", title_start + 1)
                            title_start = _skip_space(text, close + 1) if close >= 0 else title_start
                        title_end = _balanced_group(text, title_start)
                        if title_end:
                            body_start, body_end = title_start + 1, title_end - 1
                            title = text[body_start:body_end].strip()
                            projection_start = len(out)
                            copied = text[body_start:body_end]
                            append_text(copied, path, list(range(body_start, body_end)))
                            section_markers.append({"title": title, "start": projection_start, "path": path, "source_start": body_start, "source_end": body_end})
                            append_text("\n\n", path, [body_end, body_end])
                            index = title_end
                            continue
                    if name in {"href", "hyperref"}:
                        first = _balanced_group(text, after)
                        second_start = _skip_space(text, first) if first else after
                        second = _balanced_group(text, second_start)
                        if first and second:
                            body_start, body_end = second_start + 1, second - 1
                            append_text(text[body_start:body_end], path, list(range(body_start, body_end)))
                            index = second
                            continue
                    if name in DROP_COMMANDS:
                        cursor = command.end()
                        while cursor < len(text) and text[cursor] == "[":
                            close = text.find("]", cursor + 1)
                            cursor = len(text) if close < 0 else close + 1
                            cursor = _skip_space(text, cursor)
                        group_end = _balanced_group(text, cursor)
                        if group_end:
                            cursor = group_end
                        if name in {"newcommand", "renewcommand", "providecommand", "newenvironment", "def"}:
                            cursor = _skip_space(text, cursor)
                            if cursor < len(text) and text[cursor] == "[":
                                close = text.find("]", cursor + 1)
                                cursor = _skip_space(text, close + 1) if close >= 0 else cursor
                            body_end = _balanced_group(text, cursor)
                            if body_end:
                                cursor = body_end
                            elif name == "def":
                                line_end = text.find("\n", cursor)
                                cursor = len(text) if line_end < 0 else line_end
                            unsupported.append({"path": path, "kind": "custom_command_definition", "start": index, "end": cursor, "detail": "Custom macro definition is preserved but not analyzed as prose."})
                        if name == "includegraphics":
                            unsupported.append({"path": path, "kind": "figure_reference", "start": index, "end": cursor, "detail": "Figure asset is preserved but not analyzed as prose."})
                        if name in {"bibliography", "addbibresource", "bibliographystyle"}:
                            unsupported.append({"path": path, "kind": "bibliography_reference", "start": index, "end": cursor, "detail": "Bibliography files and citation records are preserved; reference lists are not treated as prose."})
                        index = cursor
                        continue
                    if name not in KNOWN_COMMANDS and name not in custom_definitions:
                        cursor = command.end()
                        while cursor < len(text) and text[cursor] == "[":
                            close = text.find("]", cursor + 1)
                            cursor = _skip_space(text, close + 1) if close >= 0 else cursor
                        group_end = _balanced_group(text, cursor)
                        if group_end:
                            cursor = group_end
                        unsupported.append({"path": path, "kind": "unsupported_custom_macro", "start": index, "end": cursor, "macro": name, "detail": "Custom macro is preserved in the source but excluded from prose analysis because its meaning is unknown."})
                        index = cursor
                        continue
                    # For heading and formatting commands, leave argument prose
                    # in place; remove command markup and braces from projection.
                    append_text(" ", path, [index])
                    index = command.end()
                    continue
            if text[index] in "{}":
                append_text(" ", path, [index])
            else:
                append_text(text[index], path, [index])
            index += 1
        active.pop()

    render(root)
    projection = "".join(out)
    return projection, pointers, unsupported, section_markers


def _docx_projection(content: bytes) -> tuple[str, list[SourcePointer | None], list[dict[str, Any]]]:
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("DOCX support is optional. Install it with `python -m pip install -e '.[writing-docs]'`.") from exc
    try:
        document = Document(io.BytesIO(content))
    except Exception as exc:
        raise ValueError("Could not read this DOCX document") from exc
    pieces: list[str] = []
    pointers: list[SourcePointer | None] = []
    unsupported: list[dict[str, Any]] = []

    def append_paragraph(paragraph: Any, locator: str, paragraph_index: int) -> None:
        text = "".join(run.text for run in paragraph.runs)
        if not text:
            return
        pieces.append(text)
        for run_index, run in enumerate(paragraph.runs):
            pointers.extend(SourcePointer(locator, paragraph=paragraph_index, run=run_index, run_offset=offset) for offset in range(len(run.text)))
        pieces.append("\n\n")
        pointers.extend([None, None])

    for paragraph_index, paragraph in enumerate(document.paragraphs):
        append_paragraph(paragraph, "body", paragraph_index)
    if document.tables:
        unsupported.append({"path": "document.xml", "kind": "docx_tables", "detail": "Table content is not included in the editable prose projection in this version."})
    text = "".join(pieces).rstrip()
    return text, pointers[:len(text)], unsupported


def _pdf_projection(filename: str, content: bytes) -> tuple[str, list[SourcePointer | None], list[dict[str, Any]], str]:
    extracted = extract_document(filename, content)
    try:
        import pymupdf
        doc = pymupdf.open(stream=content, filetype="pdf")
        pieces: list[str] = []
        pointers: list[SourcePointer | None] = []
        for page_number, page in enumerate(doc, start=1):
            page_text = page.get_text("text", sort=True).strip()
            if not page_text:
                continue
            marker = f"[Page {page_number}]\n"
            pieces.extend((marker, page_text, "\n\n"))
            pointers.extend([None] * len(marker))
            pointers.extend(SourcePointer("pdf", page=page_number) for _ in page_text)
            pointers.extend([None, None])
        text = "".join(pieces).rstrip()
        return text, pointers[:len(text)], [], extracted["extraction"]
    except ImportError:
        # extract_document already raises a clear optional-dependency error.
        raise


def import_manuscript(filename: str, content: bytes) -> DocumentBundle:
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 25 MiB local import limit")
    suffix = Path(filename).suffix.casefold()
    if suffix not in SUPPORTED:
        raise ValueError("Choose a .tex, .zip, .docx, .txt or text-layer .pdf manuscript")
    digest = hashlib.sha256(content).hexdigest()
    name = Path(filename).name
    unsupported: list[dict[str, Any]] = []

    if suffix == ".txt":
        text = _decode(name, content)
        pointers = [SourcePointer(name, offset=index) for index in range(len(text))]
        return DocumentBundle(name, "txt", name, {name: content}, {name: text}, text, pointers, [], [], True, "UTF-8 text source; exact character map", digest)

    if suffix == ".tex":
        root = name
        sources = {root: _decode(root, content)}
        projection, pointers, unsupported, section_markers = _tex_projection(root, sources)
        unsupported.extend({"path": root, "kind": "external_project_reference", "detail": "A single .tex file cannot resolve sibling inputs, bibliography, style files, or figures; upload the complete project ZIP for full source context."} for _ in [0] if re.search(r"\\(?:input|include|subfile|includegraphics|addbibresource|bibliography)\b", sources[root]))
        return DocumentBundle(name, "tex", root, {root: content}, sources, projection, pointers, unsupported, section_markers, True, "LaTeX prose projection; single-file includes are unresolved", digest)

    if suffix == ".zip":
        files = _zip_files(content)
        sources = {path: _decode(path, value) for path, value in files.items() if Path(path).suffix.casefold() in {".tex", ".bib", ".sty", ".cls", ".txt"}}
        root = _choose_root(sources)
        projection, pointers, unsupported, section_markers = _tex_projection(root, sources)
        return DocumentBundle(name, "zip", root, files, sources, projection, pointers, unsupported, section_markers, True, "LaTeX root and recursive input/include projection; original archive files retained", digest)

    if suffix == ".docx":
        projection, pointers, unsupported = _docx_projection(content)
        return DocumentBundle(name, "docx", None, {name: content}, {}, projection, pointers, unsupported, [], True, "DOCX paragraph text with run-level source mapping; tables excluded", digest)

    projection, pointers, unsupported, extraction = _pdf_projection(name, content)
    unsupported.append({"path": name, "kind": "pdf_read_only", "detail": "PDF is a text-layer projection and cannot be written back to the original source."})
    return DocumentBundle(name, "pdf", None, {name: content}, {}, projection, pointers, unsupported, [], False, extraction, digest)


def map_projection_span(bundle: DocumentBundle, start: int, end: int, visible_text: str) -> dict[str, Any]:
    if start < 0 or end <= start or end > len(bundle.projection) or len(bundle.pointers) < end:
        return {"editable": False, "reason": "The extracted passage has no stable source mapping."}
    mapped = [pointer for pointer in bundle.pointers[start:end] if pointer is not None]
    if not mapped:
        return {"editable": False, "reason": "This passage is outside mapped prose."}
    first = mapped[0]
    if bundle.format in {"txt", "tex", "zip"}:
        expected = list(range(first.offset or 0, (first.offset or 0) + len(mapped)))
        exact = first.offset is not None and all(item.path == first.path for item in mapped) and [item.offset for item in mapped] == expected
        source_text = bundle.source_texts.get(first.path, "")
        source_start = first.offset
        source_end = source_start + len(mapped) if source_start is not None else None
        exact = exact and source_end is not None and source_text[source_start:source_end] == visible_text
        return {"editable": bool(exact), "path": first.path, "start": source_start, "end": source_end, "reason": None if exact else "LaTeX markup or an include boundary crosses this sentence; editing it could damage source structure."}
    if bundle.format == "docx":
        same_run = all(item.path == first.path and item.paragraph == first.paragraph and item.run == first.run for item in mapped)
        offsets = [item.run_offset for item in mapped]
        contiguous = bool(offsets) and offsets == list(range(offsets[0] or 0, (offsets[0] or 0) + len(offsets)))
        exact = same_run and contiguous
        return {"editable": exact, "block": "body", "paragraph": first.paragraph, "run": first.run, "start": offsets[0] if offsets else None, "end": offsets[-1] + 1 if offsets else None, "reason": None if exact else "The sentence crosses DOCX runs; edit is read-only to preserve document formatting."}
    if bundle.format == "pdf":
        pages = sorted({item.page for item in mapped if item.page is not None})
        return {"editable": False, "page": pages[0] if len(pages) == 1 else None, "reason": "PDF text extraction is read-only; source layout cannot be preserved."}
    return {"editable": False, "reason": "Unsupported source mapping."}
