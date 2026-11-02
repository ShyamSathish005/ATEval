"""Transparent baseline diagnostics and conservative edit proposals.

All measurements are descriptive. Suggestions never modify source text and
must be explicitly accepted by an author.
"""

from __future__ import annotations

import hashlib
import re
import statistics
from collections import Counter
from typing import Any, Iterable

from .editing import suggestions_for_text
from .latex import protected_spans
from ..revisions.recommendation import recommend_edits

WORD_RE = re.compile(r"[\w]+(?:[’'-][\w]+)*", re.UNICODE)
SENTENCE_END_RE = re.compile(r"[.!?]+(?:[\"'’”)}\]]*)\s+")
SECTION_RE = re.compile(r"(?m)^\s*(?:#{1,6}\s+.+|\\(?:part|chapter|section|subsection|subsubsection)\*?\s*\{[^}]+\}|(?:abstract|introduction|methods?|results?|discussion|conclusion|limitations?)\s*:?\s*)$")

STOP_WORDS = frozenset("""a an the and or but if while when as at by for from in into of on onto to with without within is are was were be been being am do does did have has had can could may might must shall should will would this that these those it its we our they their he she you your which who what where how not no nor than then there here also such very more most less many much each both all any some only other another same different however therefore thus because since although though whereas moreover furthermore first second third finally generally specifically particularly often usually clearly""".split())

def _words(text: str) -> list[str]:
    return [match.group(0).casefold() for match in WORD_RE.finditer(text)]


def _sentences(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    start = 0
    for match in SENTENCE_END_RE.finditer(text):
        end = match.start() + len(match.group(0).rstrip())
        sentence = text[start:end].strip()
        if sentence:
            left = start + len(text[start:end]) - len(text[start:end].lstrip())
            spans.append((left, end, sentence))
        start = match.end()
    tail = text[start:]
    if tail.strip():
        left = start + len(tail) - len(tail.lstrip())
        spans.append((left, len(text), tail.strip()))
    return spans


def _paragraphs(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, re.S)]


def _sections(text: str) -> list[dict[str, Any]]:
    headings = list(SECTION_RE.finditer(text))
    if not headings:
        return [{"title": "Document", "start": 0, "end": len(text)}] if text.strip() else []
    sections = []
    if headings[0].start() > 0 and text[:headings[0].start()].strip():
        sections.append({"title": "Document front matter", "start": 0, "end": headings[0].start()})
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        label = heading.group(0).strip().lstrip("# ").rstrip(":")
        tex_title = re.search(r"\{([^}]+)\}", label)
        if tex_title:
            label = tex_title.group(1)
        sections.append({"title": label, "start": heading.start(), "end": end})
    return sections


def _syllables(word: str) -> int:
    word = word.casefold()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1 and not word.endswith(("le", "ye")):
        count -= 1
    if word.endswith("es") and len(word) > 3 and count > 1:
        count -= 1
    return max(1, count)


def _mtld(tokens: list[str], threshold: float = 0.72) -> float | None:
    """Forward/reverse MTLD estimate; descriptive only, not a quality score."""
    if len(tokens) < 20:
        return None

    def factors(items: Iterable[str]) -> float:
        factor_count = 0.0
        seen: set[str] = set()
        count = 0
        for token in items:
            seen.add(token)
            count += 1
            ttr = len(seen) / count
            if ttr <= threshold:
                factor_count += 1.0
                seen.clear()
                count = 0
        if count and seen:
            final_ttr = len(seen) / count
            if final_ttr < 1.0:
                factor_count += (1.0 - final_ttr) / (1.0 - threshold)
            else:
                factor_count += 1.0
        return factor_count

    total_factors = factors(tokens) + factors(reversed(tokens))
    return round((2 * len(tokens) / total_factors), 2) if total_factors else None


def _dependency_depth(token: Any) -> int:
    depth = 0
    current = token
    seen = {token.i}
    while current.head != current and current.head.i not in seen:
        current = current.head
        seen.add(current.i)
        depth += 1
    return depth


def analyze_text(text: str, *, document_name: str = "Untitled document", document_format: str = "txt") -> dict[str, Any]:
    """Analyze writing and return traceable, review-only suggestions."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if len(text) > 2_000_000:
        raise ValueError("Text exceeds the 2,000,000-character analysis limit")
    tokens = _words(text)
    sentences = _sentences(text)
    paragraphs = _paragraphs(text)
    sections = _sections(text)
    protected = protected_spans(text)
    sent_lengths = [len(_words(sentence)) for _, _, sentence in sentences if _words(sentence)]
    unique = len(set(tokens))
    trigrams = Counter(tuple(tokens[i:i + 3]) for i in range(max(0, len(tokens) - 2)))
    repeated_trigrams = [{"phrase": " ".join(gram), "count": count} for gram, count in trigrams.most_common(20) if count > 1]
    paragraph_terms = [set(token for token in _words(p) if token not in STOP_WORDS and len(token) > 2) for _, _, p in paragraphs]
    adjacent_overlap = []
    for i in range(len(paragraph_terms) - 1):
        left, right = paragraph_terms[i], paragraph_terms[i + 1]
        union = left | right
        adjacent_overlap.append(round(len(left & right) / len(union), 3) if union else 0.0)

    candidates = []
    claim_pattern = re.compile(r"\b(?:we (?:show|find|found|demonstrate|observe|observed|argue|propose)|results? (?:show|suggest|indicate)|this (?:suggests|indicates|demonstrates))\b", re.I)
    for start, end, sentence in sentences:
        markers = [m.group(0) for m in claim_pattern.finditer(sentence)]
        if markers:
            local_protected = any(start < span["end"] and end > span["start"] for span in protected)
            candidates.append({"start": start, "end": end, "text": sentence, "claim_cue": markers[0], "protected_span_nearby": local_protected, "interpretation": "heuristic candidate; verify claim and supporting evidence manually"})

    acronym_definitions = re.findall(r"\b([A-Z][A-Za-z-]{3,}(?:\s+[A-Z][A-Za-z-]{2,}){0,5})\s*\(([A-Z]{2,10})\)", text)
    defined_acronyms = sorted({abbr for _, abbr in acronym_definitions})
    revision = recommend_edits(text, protected, sections)
    suggestions = revision["suggestions"]
    repeated_sentences = []
    seen_sentences: dict[str, int] = {}
    for index, (_, _, sentence) in enumerate(sentences):
        normalized = " ".join(_words(sentence))
        if normalized and normalized in seen_sentences:
            repeated_sentences.append({"sentence_index": index + 1, "repeats_sentence_index": seen_sentences[normalized] + 1})
        elif normalized:
            seen_sentences[normalized] = index

    syllable_count = sum(_syllables(word) for word in tokens)
    sentence_count = len(sent_lengths)
    flesch = None
    if len(tokens) >= 30 and sentence_count:
        flesch = round(206.835 - 1.015 * (len(tokens) / sentence_count) - 84.6 * (syllable_count / len(tokens)), 1)
    length_std = round(statistics.pstdev(sent_lengths), 2) if len(sent_lengths) > 1 else (0.0 if sent_lengths else None)
    average_length = round(statistics.mean(sent_lengths), 2) if sent_lengths else None
    sentence_variation = round(length_std / average_length, 3) if length_std is not None and average_length else None
    lexical_density = round(sum(1 for token in tokens if token not in STOP_WORDS) / len(tokens), 3) if tokens else None
    repeated_token_types = [{"token": token, "count": count} for token, count in Counter(tokens).most_common(25) if count >= 4 and token not in STOP_WORDS]

    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm", disable=["ner", "textcat"])
            doc = nlp(text[:1_000_000])
            parsed_tokens = [token for token in doc if not token.is_space and not token.is_punct]
            syntax = {
                "parser": nlp.meta.get("name", "spaCy model"),
                "parsed_token_count": len(parsed_tokens),
                "clause_like_verbs_per_100_tokens": round(100 * sum(token.pos_ in {"VERB", "AUX"} for token in parsed_tokens) / max(1, len(parsed_tokens)), 2),
                "mean_dependency_depth": round(statistics.mean(_dependency_depth(token) for token in parsed_tokens), 2) if parsed_tokens else None,
            }
        except OSError:
            syntax = {"parser": "unavailable", "reason": "Install an authorized local English spaCy pipeline; none was downloaded."}
    except ImportError:
        syntax = {"parser": "unavailable", "reason": "Optional spaCy package is not installed."}

    return {
        "schema_version": "writing-analysis-v1",
        "document": {"name": document_name, "format": document_format, "characters": len(text), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()},
        "counts": {"words": len(tokens), "unique_words": unique, "sentences": len(sentences), "paragraphs": len(paragraphs), "sections": len(sections), "protected_spans": len(protected)},
        "lexical": {"type_token_ratio_length_sensitive": round(unique / len(tokens), 3) if tokens else None, "mtld_threshold_0_72": _mtld(tokens), "heuristic_lexical_density": lexical_density, "frequent_content_words": repeated_token_types},
        "sentence": {"mean_words": average_length, "population_sd_words": length_std, "coefficient_of_variation": sentence_variation, "flesch_reading_ease_english_30_word_minimum": flesch},
        "discourse": {"adjacent_paragraph_content_word_jaccard": adjacent_overlap, "repeated_content_trigrams": repeated_trigrams, "repeated_sentences": repeated_sentences},
        "structure": {"sections": [{"title": s["title"], "start": s["start"], "end": s["end"]} for s in sections], "defined_acronyms": defined_acronyms, "claim_cue_candidates": candidates},
        "syntax": syntax,
        "protected_spans": protected,
        "suggestions": suggestions,
        "revision": revision,
        "interpretation_limits": [
            "Linguistic features describe this text; they are not an ideal or universal human-writing profile.",
            "Lexical diversity, sentence length, cohesion, and readability depend on text length, genre, topic, discipline, language, and audience.",
            "Claim/evidence and paragraph-cohesion outputs are heuristic cues, not semantic validation.",
            "Every suggestion can change nuance. Review each one; the original document is never modified by analysis.",
        ],
    }
