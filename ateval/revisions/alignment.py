"""CPU-friendly monotonic sentence alignment and transparent edit spans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

WORD_RE = re.compile(r"[\w]+(?:[’'-][\w]+)*", re.UNICODE)
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?:[\"'’”)}\]]*)\s+(?=[A-Z0-9\\])")


@dataclass(frozen=True)
class TextUnit:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Alignment:
    before_indices: tuple[int, ...]
    after_indices: tuple[int, ...]
    operation: str
    score: float


def split_sentences(text: str) -> list[TextUnit]:
    units: list[TextUnit] = []
    start = 0
    for boundary in SENTENCE_BOUNDARY.finditer(text):
        raw = text[start:boundary.start()]
        left = start + len(raw) - len(raw.lstrip())
        right = start + len(raw.rstrip())
        if left < right:
            units.append(TextUnit(text[left:right], left, right))
        start = boundary.end()
    tail = text[start:]
    left = start + len(tail) - len(tail.lstrip())
    right = start + len(tail.rstrip())
    if left < right:
        units.append(TextUnit(text[left:right], left, right))
    return units


def _tokens(text: str) -> set[str]:
    return {match.group(0).casefold() for match in WORD_RE.finditer(text)}


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    normalized = " ".join(WORD_RE.findall(text.casefold()))
    if len(normalized) < n:
        return {normalized} if normalized else set()
    return {normalized[i:i + n] for i in range(len(normalized) - n + 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _similarity(left: str, right: str) -> float:
    token = _jaccard(_tokens(left), _tokens(right))
    chars = _jaccard(_char_ngrams(left), _char_ngrams(right))
    lengths = len(_tokens(left)), len(_tokens(right))
    length = min(lengths) / max(lengths) if max(lengths) else 1.0
    return 0.55 * token + 0.30 * chars + 0.15 * length


def align_sentences(before: list[str], after: list[str], *, gap_penalty: float = 0.42, minimum_similarity: float = 0.16) -> list[Alignment]:
    """Globally align sentence sequences using a monotonic DP baseline.

    Supports 1:1, 1:2, and 2:1 alignments plus insert/delete. It is a
    reproducible non-neural comparator, not the published neural CRF model.
    """
    n, m = len(before), len(after)
    scores = [[float("-inf")] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[int, int, str, float] | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    scores[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            base = scores[i][j]
            if base == float("-inf"):
                continue
            choices: list[tuple[int, int, str, float]] = []
            if i < n and j < m:
                sim = _similarity(before[i], after[j])
                match = 3.0 * sim - 0.68 if sim >= minimum_similarity else -1.25
                choices.append((i + 1, j + 1, "match" if sim >= minimum_similarity else "replace", match))
            if i < n and j + 1 < m:
                sim = _similarity(before[i], f"{after[j]} {after[j + 1]}")
                match = 3.0 * sim - 0.78 if sim >= minimum_similarity else -1.35
                choices.append((i + 1, j + 2, "split", match))
            if i + 1 < n and j < m:
                sim = _similarity(f"{before[i]} {before[i + 1]}", after[j])
                match = 3.0 * sim - 0.78 if sim >= minimum_similarity else -1.35
                choices.append((i + 2, j + 1, "merge", match))
            if i < n:
                choices.append((i + 1, j, "delete", -gap_penalty))
            if j < m:
                choices.append((i, j + 1, "insert", -gap_penalty))
            for ni, nj, operation, delta in choices:
                candidate = base + delta
                if candidate > scores[ni][nj]:
                    scores[ni][nj] = candidate
                    back[ni][nj] = (i, j, operation, delta)

    result: list[Alignment] = []
    i, j = n, m
    while i or j:
        step = back[i][j]
        if step is None:
            raise RuntimeError("alignment path is incomplete")
        pi, pj, operation, score = step
        result.append(Alignment(tuple(range(pi, i)), tuple(range(pj, j)), operation, round(score, 4)))
        i, j = pi, pj
    return list(reversed(result))


def extract_edit_spans(before: str, after: str) -> list[dict[str, Any]]:
    """Return exact character offsets for contiguous changed spans.

    The output is a transparent diff baseline; it does not infer edit intent.
    """
    matcher = SequenceMatcher(a=before, b=after, autojunk=False)
    spans = []
    for tag, before_start, before_end, after_start, after_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        spans.append({
            "operation": {"insert": "A", "delete": "D", "replace": "R"}[tag],
            "before_start": before_start,
            "before_end": before_end,
            "after_start": after_start,
            "after_end": after_end,
            "before": before[before_start:before_end] or None,
            "after": after[after_start:after_end] or None,
        })
    return spans
