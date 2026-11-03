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
| Citation preservation | Rejected | 0.913 s | Protected sentinel missing |
| Equation/reference preservation | Rejected | 1.264 s | Protected sentinels missing |
| Difficult technical claim | Expert review required | 0.000 s | Generation intentionally not started |

The generated candidates were inspected by the SCAR gates. The model
successfully produced real revisions, but it did not reliably preserve
citation/equation sentinels in this configuration. Therefore the
technical-preservation launch gate is **not passed**, and this model is not
declared production-ready. Rejection is the correct safety behavior.

The configured API now uses the safety-aware `ateval` prompt mode rather than
the legacy `published` mode. This prevents a known integration defect where
the published prompt omitted the protected-sentinel contract, but the model
still requires a stronger preservation-capable configuration before release.

The full machine-readable output was generated at
`/tmp/ateval-alpha-model-smoke-v2.json` during validation and is intentionally
not committed because it contains generated proposal text, even though the
fixture is synthetic.
