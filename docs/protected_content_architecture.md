# Protected content architecture

## Purpose

Generation models are probabilistic. A prompt asking a model to preserve numbers or citations does not enforce that behavior. SCAR therefore replaces protected spans in the selected editable passage with typed, unique sentinels before inference and validates them outside the model afterward.

Implementation: [`protected_content.py`](../ateval/revisions/protected_content.py).

## Protected span types

The current deterministic recognizer protects:

- Numeric expressions, common units, percentages, number words, and common statistical expressions.
- Numeric bracket citations, author-year citations, LaTeX citation/reference commands, and reference commands.
- LaTeX math delimiters and equation/code environments.
- URLs and inline/fenced code.
- Technical identifiers, mixed-case/camel-case identifiers, and acronym-like tokens.
- Every occurrence of author-specified terminology.

Patterns are conservative and ordered. Overlapping matches become one non-overlapping span so a full equation, citation command, code fragment, or model identifier is not split into competing placeholders. The citation matcher was narrowed after M4.1 incorrectly read `[URL]` as a citation.

## Mapping and sentinel construction

`protect_content(text, protected_terms)` returns a `ProtectedText` with:

- Original and protected text.
- SHA-256 of the source.
- For every span: sentinel, exact original content, type, character offsets, SHA-256, and expected occurrence count.
- One deterministic sentinel per occurrence, derived from type, span hash, and position.

Example form: `⟪ATEVAL_NUMBER_UNIT_<span-hash>_0001⟫`. The map is serializable for audit/reproducibility and never asks the model to infer the original value.

## Validation contract

`validate_and_restore(candidate, mapping)` applies these steps:

1. Count every expected sentinel and reject if one is missing or duplicated.
2. Reject any sentinel-shaped token that was not in the map.
3. Restore exact original strings only after sentinel checks pass.
4. Re-scan the reconstructed candidate and compare its ordered protected-span sequence with the original mapping. Any inserted, deleted, reordered, or altered protected value is a failure.
5. Compare LaTeX `\\begin`/`\\end` environment sequences and verify properly nested, balanced environment pairs. Mismatches fail closed.
6. Return `restored_text=None` on every failure. The system does not silently paste a missing source value back into an unknown sentence.

The final check catches model-added raw numbers/citations as well as damaged placeholders. In SCAR a failed check returns `REJECT_STRUCTURAL_CHANGE`; the draft remains unchanged. All validation results state `semantic_equivalence: not_assessed`.

## Scope and limitations

This is exact string/structure protection, not a semantic model. It cannot detect all values expressed indirectly, every domain-specific unit, paraphrased technical names, or a scientifically incorrect relationship between correctly preserved terms. Number words are protected because they can encode result counts, but common prose words such as “one” or “first” can consequently become non-editable spans. Authors can add terms for the active request.

The initial version protects the selected sentence/passage. The adjacent paragraph context is read-only input to the model and is not copied into the returned patch. The surrounding document text is retained verbatim by applying an accepted patch only at the selected offsets. Full-document cross-reference resolution and actual LaTeX compilation remain separate validation work.

The current span families and sentinel strategy reuse established constrained-editing ideas. The ATEval-specific application and evaluation design are research prototypes, not a novelty claim. See [`scar_algorithm_specification.md`](scar_algorithm_specification.md) for comparison with prior work.
