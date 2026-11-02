"""Protected-span discovery for LaTeX and academic source text."""

from __future__ import annotations

import hashlib
import re
from typing import Any

PROTECTED_RE = re.compile(
    r"(?s)\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?|math|verbatim|lstlisting|minted)\}.*?\\end\{(?:equation\*?|align\*?|gather\*?|multline\*?|math|verbatim|lstlisting|minted)\}"
    r"|\\\[.*?\\\]|\\\(.*?\\\)|\$\$.*?\$\$|(?<!\\)\$(?!\$).*?(?<!\\)\$"
    r"|\\(?:cite[a-zA-Z*]*|parencite|textcite|autocite|ref|eqref|label|bibitem|bibliography|addbibresource|url|href)\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}"
    r"|\[(?:\d+(?:\s*[,;–-]\s*\d+)*)\]|\[(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\]"
    r"|\((?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?)(?:;\s*[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?)*\)"
    r"|(?:\[[0-9,;\s-]+\]|https?://\S+|`[^`]+`)"
    r"|(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?(?:\s*(?:×|\*|±|\+/-|%|‰|°|mm|cm|m|km|µm|nm|kg|mg|g|ml|mL|L|s|ms|min|h|Hz|kHz|MHz|GHz|Pa|kPa|MPa|GPa|V|mV|W|kW|J|kJ|eV|K|°C|°F|mol|mmol|M|mM|µM|nM|dB|dpi|fps|ppm|ppb))?(?!\w)"
)


def protected_spans(text: str) -> list[dict[str, Any]]:
    return [{"start": m.start(), "end": m.end(), "kind": "math/citation/reference/code/URL/number", "sha256": hashlib.sha256(m.group(0).encode("utf-8")).hexdigest()} for m in PROTECTED_RE.finditer(text)]


def overlaps(start: int, end: int, spans: list[dict[str, Any]]) -> bool:
    return any(start < span["end"] and end > span["start"] for span in spans)
