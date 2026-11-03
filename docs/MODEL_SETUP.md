# Local model setup

Generation is optional and local. ATEval does not download weights or send
manuscript text to a remote provider. The supported runtime path is a
loopback Ollama server:

```sh
ollama serve
ollama list
export ATEVAL_OLLAMA_MODEL='your-installed-model'
./.venv/bin/python scripts/smoke_test_local_model.py
```

The smoke test requires the model to be installed and runs grammar, clarity,
structure, redundancy, no-op, citation, equation/reference, numeric, and
technical-term scenarios. It records Ollama version, configured model,
runtime, context length, generation settings, latency, and SCAR outcomes.
It exits non-zero when Ollama, the model, or a scenario fails.

The 2026-11-03 smoke test executed the installed `ateval-xtragpt-1_5b-q8_0`
model on an Apple M1. It produced real clarity and restructuring proposals,
correctly abstained on a no-op, and passed citation/equation-reference
preservation after exact-source canonicalization. See [the full result](./MODEL_SMOKE_TEST_2026-11-03.md).
Unsafe or unsupported output remains rejected.

Historical XtraGPT-1.5B output is experimental research evidence, not a
semantic-equivalence guarantee. The API uses loopback-only
Ollama URLs, a 2,048-token context, 192 maximum output tokens, temperature
0.1, and seed 17.
