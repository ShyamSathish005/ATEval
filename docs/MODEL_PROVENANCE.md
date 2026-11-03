# Model Provenance

## Model under investigation

`ateval-xtragpt-1_5b-q8_0`

The local GGUF artifact has not been acquired or bundled. This record therefore
does not establish the identity, hash, quantization, or redistribution rights
of a particular model file.

## Available evidence

| Field | Observed or reported value | Evidence | Status |
|---|---|---|---|
| Ollama model name | `ateval-xtragpt-1_5b-q8_0` | [`MODEL_SMOKE_TEST_2026-11-03.md`](MODEL_SMOKE_TEST_2026-11-03.md) | Observed locally |
| Base model | Reported as `Qwen/Qwen2.5-1.5B-Instruct` | [`MODEL_LICENSES.md`](../MODEL_LICENSES.md) | Not independently verified |
| Reported checkpoint license | `MG0-2.0` | [`MODEL_LICENSES.md`](../MODEL_LICENSES.md) | Not independently verified |
| Reported base-model license | Apache-2.0 | [`MODEL_LICENSES.md`](../MODEL_LICENSES.md) | Upstream claim only |
| Runtime quantization | `Q8_0` | [`MODEL_SMOKE_TEST_2026-11-03.md`](MODEL_SMOKE_TEST_2026-11-03.md) | Runtime metadata only |
| Context length | 2048 tokens | [`MODEL_SMOKE_TEST_2026-11-03.md`](MODEL_SMOKE_TEST_2026-11-03.md) | Runtime configuration |
| GGUF file in repository | None | Repository inspection | Verified absent |
| Modelfile in repository | None | Repository inspection | Verified absent |
| Checkpoint revision and SHA-256 | Not established | No local artifact | Unverified |

## Distribution decision

The application does not automatically download or redistribute model weights.
The model path is caller-provided through `ATEVAL_XTRAGPT_GGUF` or the
`--model-file` CLI option. Users must obtain and license a compatible model
independently.

No model-weight provenance or redistribution claim should be inferred from the
Ollama model name alone. Before distributing a model, obtain the exact artifact,
calculate its SHA-256, inspect its GGUF metadata, confirm its license, and
document the corresponding Modelfile and source.

## Remaining limitations

- The exact checkpoint and upstream revision are unresolved.
- A runtime quantization label does not prove the source file's quantization.
- The published model claims do not prove that the local Ollama model is the
  same artifact.
- Training-data provenance and downstream obligations remain unverified for
  the local artifact.
