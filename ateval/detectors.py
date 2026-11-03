"""Deterministic, uncalibrated AI-writing signal baseline.

This is a research diagnostic, not an authorship classifier. It reports
stylometric features and a heuristic signal for review; it has no training
data, calibration, or authorship ground truth.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from typing import Any

WORD_RE = re.compile(r"[\w]+(?:[’'-][\w]+)*", re.UNICODE)
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)", re.S)
FUNCTION_WORDS = frozenset(
    "a an the and or but if while when as at by for from in into of on to with "
    "is are was were be been being have has had can could may might must should "
    "will would this that these those it its we our they their which who not".split()
)


def _words(text: str) -> list[str]:
    return [match.group(0).casefold() for match in WORD_RE.finditer(text)]


def _sentences(text: str) -> list[str]:
    return [match.group(0).strip() for match in SENTENCE_RE.finditer(text) if match.group(0).strip()]


def _bounded(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 4)


def evaluate_stylometric_baseline(text: str) -> dict[str, Any]:
    """Return reproducible features and an uncalibrated research signal."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("text must not be empty")
    words = _words(text)
    sentences = _sentences(text)
    if not words:
        raise ValueError("text must contain at least one word")
    lengths = [len(_words(sentence)) for sentence in sentences if _words(sentence)]
    counts = Counter(words)
    unique = len(counts)
    trigrams = Counter(tuple(words[index:index + 3]) for index in range(max(0, len(words) - 2)))
    repeated_trigrams = sum(count - 1 for count in trigrams.values() if count > 1)
    punctuation = sum(1 for char in text if char in ",;:!?()[]{}")
    function_ratio = sum(counts[word] for word in FUNCTION_WORDS) / len(words)
    mean_length = statistics.mean(lengths) if lengths else 0.0
    variation = statistics.pstdev(lengths) / mean_length if len(lengths) > 1 and mean_length else 0.0
    lexical_uniformity = 1.0 - min(1.0, (unique / len(words)) / 0.75)
    repetition = min(1.0, repeated_trigrams / max(1, len(words) - 2))
    low_variation = 1.0 - min(1.0, variation / 0.8)
    punctuation_regular = 1.0 - min(1.0, (punctuation / len(words)) / 0.25)
    signal = _bounded(
        0.35 * lexical_uniformity
        + 0.30 * low_variation
        + 0.20 * repetition
        + 0.15 * punctuation_regular
    )
    uncertainty = _bounded(0.65 + (0.25 if len(words) < 80 else 0.0) - 0.15 * min(1.0, len(words) / 500))
    return {
        "detector_name": "stylometric-baseline",
        "detector_version": "m5.0.0",
        "status": "experimental_unvalidated",
        "signal_score": signal,
        "uncertainty": uncertainty,
        "interpretation": "research signal only; not an authorship classifier or evidence of AI authorship",
        "features": {
            "word_count": len(words),
            "sentence_count": len(lengths),
            "type_token_ratio": round(unique / len(words), 4),
            "sentence_length_mean": round(mean_length, 4),
            "sentence_length_variation": round(variation, 4),
            "function_word_ratio": round(function_ratio, 4),
            "punctuation_density": round(punctuation / len(words), 4),
            "repeated_trigram_rate": round(repetition, 4),
        },
        "limitations": [
            "No labelled AI-versus-human dataset was available for calibration.",
            "Features vary with discipline, genre, editing, language, and passage length.",
            "The signal must not be converted into an authorship probability.",
        ],
    }


def evaluate_passages(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for passage in passages:
        result = evaluate_stylometric_baseline(str(passage["text"]))
        results.append({**passage, "analysis_status": "analyzed", "highlight_state": "review",
                        "method_results": [result], "signal_note": result["interpretation"]})
    return results
