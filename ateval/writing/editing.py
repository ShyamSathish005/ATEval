"""Conservative academic phrase suggestions and exact-span application."""

from __future__ import annotations

import re
import uuid
from typing import Any

from .latex import overlaps

PHRASE_RULES: tuple[tuple[str, str, str, str], ...] = (
    (r"\bin order to\b", "to", "concision", "Consider removing the wordier equivalent if it does not change emphasis."),
    (r"\bdue to the fact that\b", "because", "concision", "Check that the causal relationship is intended before accepting."),
    (r"\bat this point in time\b", "now", "concision", "Use only if the time reference is exactly current."),
    (r"\bin the event that\b", "if", "concision", "Check that the condition is not meant to imply a contingency with a different scope."),
    (r"\bhas the ability to\b", "can", "concision", "Check that ability, rather than permission or opportunity, is intended."),
    (r"\bis able to\b", "can", "concision", "Check that ability, rather than permission or opportunity, is intended."),
    (r"\ba number of\b", "several", "concision", "Retain the original if the amount is intentionally unspecified."),
    (r"\bfor the purpose of\b", "to", "concision", "Check that purpose and result are not being conflated."),
)


def suggestions_for_text(text: str, protected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions = []
    for pattern, replacement, intent, note in PHRASE_RULES:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if overlaps(match.start(), match.end(), protected):
                continue
            source = match.group(0)
            replacement_text = replacement.upper() if source.isupper() else replacement.capitalize() if source.istitle() else replacement
            suggestions.append({"id": uuid.uuid5(uuid.NAMESPACE_URL, f"{match.start()}:{match.end()}:{source}:{replacement_text}").hex[:16], "start": match.start(), "end": match.end(), "source": source, "replacement": replacement_text, "intent": intent, "reason": note, "risk": "review", "review_required": True})
    return sorted(suggestions, key=lambda item: item["start"])


def apply_accepted_suggestions(text: str, suggestions: list[dict[str, Any]], accepted_ids: set[str]) -> tuple[str, list[dict[str, Any]]]:
    selected = sorted((item for item in suggestions if item["id"] in accepted_ids), key=lambda item: item["start"], reverse=True)
    out = text
    applied: list[dict[str, Any]] = []
    last_start = len(text) + 1
    for item in selected:
        start, end = int(item["start"]), int(item["end"])
        if start < 0 or end > len(text) or start >= end or end > last_start or text[start:end] != item["source"]:
            continue
        out = out[:start] + item["replacement"] + out[end:]
        applied.append({"id": item["id"], "start": start, "end": end, "before": item["source"], "after": item["replacement"], "intent": item["intent"], "reason": item["reason"]})
        last_start = start
    return out, list(reversed(applied))
