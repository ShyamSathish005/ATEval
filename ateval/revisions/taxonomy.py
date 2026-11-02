"""Research crosswalk retaining the original corpus intention label."""

from __future__ import annotations

import re

INTENTS = (
    "grammar_correction",
    "clarity_improvement",
    "concision",
    "redundancy_removal",
    "vocabulary_refinement",
    "sentence_restructuring",
    "explanation_improvement",
    "argument_clarification",
    "cohesion_improvement",
    "paragraph_restructuring",
    "technical_precision",
    "citation_correction",
    "meaning_changed",
    "formatting",
    "author_style",
    "other",
    "no_change",
)

_ALIASES = {
    "fluency": "grammar_correction",
    "grammar": "grammar_correction",
    "grammar_correction": "grammar_correction",
    "grammar_typo": "grammar_correction",
    "correct_grammar_typo": "grammar_correction",
    "clarity": "clarity_improvement",
    "clarity_improvement": "clarity_improvement",
    "simplify": "concision",
    "concision": "concision",
    "redundancy": "redundancy_removal",
    "redundancy_removal": "redundancy_removal",
    "lang_improve_readability_simplify": "concision",
    "vocabulary": "vocabulary_refinement",
    "style": "author_style",
    "improve_style": "author_style",
    "lang_professional_improve_style": "author_style",
    "coherence": "cohesion_improvement",
    "cohesion": "cohesion_improvement",
    "cohesion_improvement": "cohesion_improvement",
    "sentence_restructuring": "sentence_restructuring",
    "paragraph_restructuring": "paragraph_restructuring",
    "meaning_changed": "meaning_changed",
    "content": "meaning_changed",
    "update_content": "meaning_changed",
    "technical_precision": "technical_precision",
    "more_accurate_specific": "technical_precision",
    "citation": "citation_correction",
    "citation_correction": "citation_correction",
    "format": "formatting",
    "adjust_format": "formatting",
    "other": "other",
    "others": "other",
    "none": "no_change",
    "no_change": "no_change",
}


def _key(label: str) -> str:
    label = re.sub(r"^<|>$", "", str(label).strip().casefold())
    label = re.sub(r"[^a-z0-9]+", "_", label).strip("_")
    return label


def canonical_intent(raw_label: str) -> str | None:
    """Map known raw labels to a product taxonomy; preserve raw label separately.

    Intent inventories differ across corpora. Unknown or granular labels stay
    unmapped until a reviewed crosswalk is added; they are never guessed.
    """
    key = _key(raw_label)
    if key in _ALIASES:
        return _ALIASES[key]
    if key.startswith("lang_accurate") or key.startswith("improve_language_more_accurate"):
        return "technical_precision"
    if key.startswith("lang_professional") or key.startswith("improve_language_improve_style"):
        return "author_style"
    if key.startswith("lang_improve_readability") or key.startswith("improve_language_simplify"):
        return "concision"
    if key.startswith("lang_other") or key.startswith("improve_language_other"):
        return "other"
    return None
