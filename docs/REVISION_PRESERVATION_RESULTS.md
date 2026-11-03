# Revision preservation results

M6.1 uses deterministic synthetic manuscripts rather than unpublished user
papers. The tests verify preservation invariants, not semantic equivalence or
human-rated writing quality.

## Verified invariants

- Approved TXT edits apply only at the exact source range.
- Stale and overlapping edits are rejected.
- Multiple accepted edits can be applied without changing untouched
  paragraphs.
- LaTeX equations, custom macros, citations, labels, cross-references, and
  figure references remain in the source outside approved ranges.
- Numeric changes are rejected when protected-content validation detects them.
- Citation and protected-term changes are rejected.
- LaTeX markup-crossing passages are non-editable.
- ZIP assets and bibliography files are retained byte-for-byte when not
  selected for editing.
- DOCX edits are limited to exact paragraph/run ranges.
- PDF imports do not offer source write-back.
- Empty model responses fail explicitly.
- Model output remains review-required, including unchanged output.

## Results

The focused M6.1 validation suite passes. The complete Python suite passes with
104 tests and two optional skips. The frontend type-check and production build
passes.

No M4.1 numerical quality comparison is reported: the frozen artifacts do not
provide a directly executable, repository-local benchmark with the same M6
eligible examples and metrics. Reusing unrelated structural counts would be a
misleading comparison. A future study should freeze a shared synthetic and
expert-reviewed corpus before comparing unnecessary edits, no-op retention,
acceptance, and academic quality.
