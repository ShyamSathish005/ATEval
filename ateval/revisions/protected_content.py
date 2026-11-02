"""Deterministic placeholder protection for scientific and user-designated spans.

This protects exact strings from generation. It is a structural invariant, not
a claim that the surrounding sentence retains its meaning.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("latex_environment", re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|math|verbatim|lstlisting|minted|tikzpicture)\}.*?\\end\{\1\}", re.S)),
    ("math", re.compile(r"\\\[.*?\\\]|\\\(.*?\\\)|\$\$.*?\$\$|(?<!\\)\$(?!\$).*?(?<!\\)\$", re.S)),
    ("latex_command", re.compile(r"\\(?:cite[a-zA-Z*]*|[pt]?cite[a-zA-Z*]*|parencite|textcite|autocite|ref|eqref|cref|Cref|label|bibitem|bibliography|addbibresource|url|href)\s*(?:\[[^\]]*\]\s*)*\{[^{}]*\}")),
    ("code", re.compile(r"```.*?```|`[^`\n]+`", re.S)),
    ("url", re.compile(r"\bhttps?://[^\s<>\]\[{}]+")),
    ("citation", re.compile(r"\[(?:\d+(?:\s*[,;–-]\s*\d+)*)\]|\[(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\]|\((?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\)(?:;\s*(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\))*")),
    ("statistic", re.compile(r"\b(?:p|t|f|r|n|N|CI|OR|RR|HR|SE|SD|IQR|AUC|F1|BLEU|ROUGE)\s*(?:=|<|>|≤|≥|≈|\bof\b)\s*[+-]?(?:\d+(?:[.,]\d+)?|\.\d+)(?:\s*(?:%|‰|\[[^\]]+\]|\([^)]*\)))?|(?<!\w)\d+(?:[.,]\d+)?\s*%\s*(?:CI|confidence interval)\b", re.I)),
    ("number_unit", re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?(?:\s*(?:×|\*|±|\+/-|%|‰|°|mm|cm|m|km|µm|nm|kg|mg|g|ml|mL|L|s|ms|min|h|Hz|kHz|MHz|GHz|Pa|kPa|MPa|GPa|V|mV|W|kW|J|kJ|eV|K|°C|°F|mol|mmol|M|mM|µM|nM|dB|dpi|fps|ppm|ppb))?(?!\w)", re.I)),
    ("number_word", re.compile(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b", re.I)),
    ("technical_identifier", re.compile(r"(?<!\w)(?:[A-Za-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*|[A-Za-z_][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+|[A-Za-z][A-Za-z0-9]*\d+[A-Za-z0-9]*(?:[-._][A-Za-z0-9]+)*)(?!\w)")),
    ("acronym", re.compile(r"(?<!\w)[A-Z][A-Z0-9]{1,9}(?:[-_][A-Z0-9]{2,})*(?!\w)")),
)

_SENTINEL_RE = re.compile(r"⟪ATEVAL_[A-Z][A-Z0-9_]*_[0-9a-f]{8,16}_[0-9]{4}⟫")
_LATEX_ENV_TOKEN_RE = re.compile(r"\\(begin|end)\s*\{([^{}]+)\}")


@dataclass(frozen=True)
class ProtectedSpan:
    sentinel: str
    original: str
    span_type: str
    start: int
    end: int
    sha256: str
    expected_occurrence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProtectedText:
    original_text: str
    protected_text: str
    source_sha256: str
    mapping: tuple[ProtectedSpan, ...]

    def mapping_dicts(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.mapping]


@dataclass(frozen=True)
class ProtectedTextValidation:
    passed: bool
    restored_text: str | None
    violations: tuple[str, ...]
    missing_sentinels: tuple[str, ...]
    duplicate_sentinels: tuple[str, ...]
    unexpected_sentinels: tuple[str, ...]
    added_protected_spans: tuple[dict[str, str], ...]
    mapping: tuple[ProtectedSpan, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "restored_text": self.restored_text,
            "violations": list(self.violations),
            "missing_sentinels": list(self.missing_sentinels),
            "duplicate_sentinels": list(self.duplicate_sentinels),
            "unexpected_sentinels": list(self.unexpected_sentinels),
            "added_protected_spans": list(self.added_protected_spans),
            "mapping": [item.to_dict() for item in self.mapping],
            "semantic_equivalence": "not_assessed",
        }


def _candidate_spans(text: str, terms: tuple[str, ...]) -> list[tuple[int, int, str]]:
    candidates: list[tuple[int, int, str]] = []
    for kind, pattern in _PATTERNS:
        candidates.extend((match.start(), match.end(), kind) for match in pattern.finditer(text) if match.end() > match.start())
    for term in sorted({item for item in terms if item}, key=lambda item: (-len(item), item.casefold())):
        cursor = 0
        while True:
            start = text.casefold().find(term.casefold(), cursor)
            if start < 0:
                break
            end = start + len(term)
            left_ok = start == 0 or not (term[0].isalnum() and text[start - 1].isalnum())
            right_ok = end == len(text) or not (term[-1].isalnum() and text[end].isalnum())
            if left_ok and right_ok:
                candidates.append((start, end, "user_term"))
            cursor = max(end, start + 1)
    # At each overlapping region, keep the earliest, longest candidate. This
    # gives equations/citations/identifiers one atomic placeholder instead of
    # overlapping placeholders for their numbers and symbols.
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0]), next((i for i, pair in enumerate(_PATTERNS) if pair[0] == item[2]), len(_PATTERNS))))
    accepted: list[tuple[int, int, str]] = []
    boundary = -1
    for candidate in candidates:
        if candidate[0] < boundary:
            continue
        accepted.append(candidate)
        boundary = candidate[1]
    return accepted


def protect_content(text: str, protected_terms: tuple[str, ...] | list[str] = ()) -> ProtectedText:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    terms = tuple(protected_terms)
    found = _candidate_spans(text, terms)
    mapping: list[ProtectedSpan] = []
    chunks: list[str] = []
    previous = 0
    counts: dict[str, int] = {}
    for index, (start, end, span_type) in enumerate(found, start=1):
        original = text[start:end]
        original_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()
        counts[span_type] = counts.get(span_type, 0) + 1
        sentinel = f"⟪ATEVAL_{span_type.upper()}_{original_hash[:12]}_{index:04d}⟫"
        if sentinel in text:
            raise ValueError("source text contains a reserved ATEval sentinel; escape or revise that literal before protection")
        chunks.extend((text[previous:start], sentinel))
        mapping.append(ProtectedSpan(sentinel, original, span_type, start, end, original_hash, 1))
        previous = end
    chunks.append(text[previous:])
    return ProtectedText(text, "".join(chunks), digest, tuple(mapping))


def validate_and_restore(candidate: str, protected: ProtectedText) -> ProtectedTextValidation:
    if not isinstance(candidate, str) or not candidate.strip():
        return ProtectedTextValidation(False, None, ("empty_candidate",), tuple(item.sentinel for item in protected.mapping), (), (), (), protected.mapping)
    expected = {item.sentinel: item for item in protected.mapping}
    seen = _SENTINEL_RE.findall(candidate)
    counts = {sentinel: seen.count(sentinel) for sentinel in expected}
    missing = tuple(sentinel for sentinel in expected if counts[sentinel] == 0)
    duplicates = tuple(sentinel for sentinel in expected if counts[sentinel] > expected[sentinel].expected_occurrence_count)
    unexpected = tuple(sorted(set(seen) - set(expected)))
    violations = []
    if missing:
        violations.append("missing_protected_sentinel")
    if duplicates:
        violations.append("duplicate_protected_sentinel")
    if unexpected:
        violations.append("unexpected_protected_sentinel")
    expected_order = [item.sentinel for item in protected.mapping]
    observed_order = [sentinel for sentinel in seen if sentinel in expected]
    if observed_order != expected_order and not (missing or duplicates):
        violations.append("protected_sentinel_order_changed")
    if violations:
        return ProtectedTextValidation(False, None, tuple(violations), missing, duplicates, unexpected, (), protected.mapping)

    restored = candidate
    # Do not silently fix or reinsert a sentinel after a failed check. We only
    # reach restoration when every placeholder is present exactly once.
    for sentinel, item in expected.items():
        restored = restored.replace(sentinel, item.original, 1)

    def latex_environment_sequence(text: str) -> list[tuple[str, str]]:
        return [(match.group(1), match.group(2)) for match in _LATEX_ENV_TOKEN_RE.finditer(text)]

    def latex_environments_balanced(sequence: list[tuple[str, str]]) -> bool:
        stack: list[str] = []
        for action, name in sequence:
            if action == "begin":
                stack.append(name)
            elif not stack or stack.pop() != name:
                return False
        return not stack

    source_environments = latex_environment_sequence(protected.original_text)
    candidate_environments = latex_environment_sequence(restored)
    if candidate_environments != source_environments:
        violations.append("latex_environment_sequence_changed")
    if not latex_environments_balanced(candidate_environments):
        violations.append("latex_environment_unbalanced")
    if violations:
        return ProtectedTextValidation(False, None, tuple(violations), (), (), (), (), protected.mapping)

    original_signature = [item.original for item in protected.mapping]
    restored_signature = [restored[start:end] for start, end, _kind in _candidate_spans(restored, tuple(item.original for item in protected.mapping if item.span_type == "user_term"))]
    if restored_signature != original_signature:
        added = tuple({"span_type": kind, "text": restored[start:end]} for start, end, kind in _candidate_spans(restored, tuple(item.original for item in protected.mapping if item.span_type == "user_term")) if restored[start:end] not in original_signature)
        violations.append("protected_span_sequence_changed")
        return ProtectedTextValidation(False, None, tuple(violations), (), (), (), added, protected.mapping)
    return ProtectedTextValidation(True, restored, (), (), (), (), (), protected.mapping)
