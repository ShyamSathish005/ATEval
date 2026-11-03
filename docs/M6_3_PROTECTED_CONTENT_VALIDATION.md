# M6.3 protected-content validation

## Finding

The configured `ateval-xtragpt-1_5b-q8_0` Ollama model did not consistently
copy Unicode ATEval sentinels. In the failing cases it returned the original
LaTeX citation or reference command unchanged, for example
`\cite{smith2024}` and `\ref{eq:one}`. This was not a parser or source-export
failure.

## Safety-preserving fix

`validate_and_restore` now canonicalizes a raw protected source occurrence only
when all of the following hold:

- The occurrence is byte-for-byte identical to the original mapped source.
- Mapped occurrences appear in their original order.
- The exact occurrence count matches the protected mapping.
- The occurrence is not inside another sentinel.

The canonicalized candidate still passes the existing sentinel, order,
LaTeX-environment, and protected-span checks. Reconstruction always uses the
original mapping, never model-generated protected text. Modified, missing,
duplicated, reordered, or unknown protected content remains fail-closed.

## Evidence

The real loopback smoke test was rerun with Ollama 0.30.11 on an Apple M1
MacBook Air (8 GB unified memory), using the locally installed
`ateval-xtragpt-1_5b-q8_0` model. Citation preservation and equation-reference
preservation changed from rejected to accepted-for-author-review after the
fix. Claim-cue changes still require expert review, and no semantic
equivalence or authorship claim is made.

The complete deterministic suite passed with `111 passed, 1 skipped`; frontend
build and site tests also passed. No TeX compiler is installed, so source-level
preservation was verified but PDF compilation was not.
