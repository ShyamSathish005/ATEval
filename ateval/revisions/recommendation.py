"""Two-stage, context-carrying recommendation facade over the CPU rule baseline."""

from __future__ import annotations

import re
from typing import Any

from .alignment import split_sentences
from .taxonomy import canonical_intent
from ..writing.editing import suggestions_for_text


def recommend_edits(text: str, protected: list[dict[str, Any]], sections: list[dict[str, Any]]) -> dict[str, Any]:
    """Stage 1 abstains unless a supported local edit cue is found.

    Stage 2 emits only the existing conservative rule proposals. Context is
    attached to each proposal for author review; the rule baseline does not
    yet use an LLM or assert that a sentence needs changing.
    """
    candidates = suggestions_for_text(text, protected)
    sentences = split_sentences(text)
    enriched = []
    for candidate in candidates:
        start, end = candidate["start"], candidate["end"]
        sentence_index = next((i for i, unit in enumerate(sentences) if unit.start <= start < unit.end), None)
        section = next((item for item in sections if item["start"] <= start < item["end"]), None)
        paragraph_start, paragraph_end = 0, len(text)
        for separator in re.finditer(r"\n[ \t]*\n", text):
            if separator.end() <= start:
                paragraph_start = separator.end()
            elif separator.start() >= end:
                paragraph_end = separator.start()
                break
        original_sentence = sentences[sentence_index].text if sentence_index is not None else text[start:end]
        previous = sentences[sentence_index - 1].text if sentence_index is not None and sentence_index > 0 else ""
        following = sentences[sentence_index + 1].text if sentence_index is not None and sentence_index + 1 < len(sentences) else ""
        intent = canonical_intent(candidate["intent"])
        enriched.append({
            **candidate,
            "issue": candidate["reason"],
            "edit_intention": intent or candidate["intent"],
            "stage_one": {"decision": "review_candidate", "basis": "supported phrase pattern; not a learned necessity classifier"},
            "context": {"paragraph": text[paragraph_start:paragraph_end].strip(), "previous_sentence": previous, "current_sentence": original_sentence, "next_sentence": following, "section": section["title"] if section else "Unknown section"},
        })
    return {
        "decision": "review_candidates" if enriched else "no_change_candidate",
        "decision_note": "No rewrite is suggested when the supported local edit patterns are absent." if not enriched else "A candidate pattern was found; the author decides whether it needs editing.",
        "suggestions": enriched,
        "generator": "rule-based-cpu-baseline-v1",
    }
