# Real local model smoke test — 2026-11-03

This report records an actual loopback Ollama run on the development machine,
not a mocked test.

## Runtime

- Model: `ateval-xtragpt-1_5b-q8_0`
- Parameter size: 1.5B
- Quantization: Q8_0
- Ollama: 0.30.11
- Hardware: Apple MacBook Air, Apple M1, 8 GB unified memory, macOS arm64
- Runtime: Ollama loopback REST API
- Context: 2,048 tokens
- Maximum output: 192 tokens
- Temperature: 0.1
- Seed: 17
- Model weights: locally installed; not bundled or redistributed

## Results

| Scenario | Result | Latency | Preservation outcome |
|---|---|---:|---|
| Grammar correction | Rejected | 0.732 s | Claim-cue change; expert review required |
| Academic clarity | Accepted for author review | 0.756 s | Structural checks passed |
| Sentence restructuring | Accepted for author review | 0.771 s | Structural checks passed |
| Repetition reduction | Rejected | 0.832 s | Claim-cue change; expert review required |
| No-op sentence | No change | 0.000 s | Abstained correctly |
| Citation preservation | Accepted for author review | rerun | Exact raw citation echo canonicalized and restored |
| Equation/reference preservation | Accepted for author review | rerun | Exact raw reference echo canonicalized and restored |
| Difficult technical claim | Expert review required | 0.000 s | Generation intentionally not started |

The first run rejected the citation and equation/reference cases because the
model copied the exact LaTeX commands instead of copying their typed sentinel
tokens. The rerun applies a conservative canonicalization step: only exact
byte-for-byte occurrences of the original protected source, in the original
order and with the expected occurrence count, are converted back to sentinels.
The original source mapping is then restored. Altered, missing, duplicated, or
reordered protected content remains rejected.

The citation and equation/reference technical-preservation scenarios therefore
passed on rerun. This does not establish semantic equivalence, and full
equation-environment generation remains a conservative source-preserving
workflow rather than a model-generated edit target.

The configured API now uses the safety-aware `ateval` prompt mode rather than
the legacy `published` mode. This prevents a known integration defect where
the published prompt omitted the protected-sentinel contract. Unsafe output
continues to fail closed; this smoke result does not replace human review.

The full machine-readable output was generated at
`/tmp/ateval-alpha-model-smoke-v2.json` during validation and is intentionally
not committed because it contains generated proposal text, even though the
fixture is synthetic.
