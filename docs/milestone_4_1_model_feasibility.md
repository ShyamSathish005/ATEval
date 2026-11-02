# Milestone 4.1 model feasibility

**Status:** XtraGPT-1.5B has run locally through Ollama on Apple M1/Metal. The full held-out run and its telemetry are recorded in [`xtragpt_1_5b_q8_0_benchmark.json`](../reports/milestone4_1/xtragpt_1_5b_q8_0_benchmark.json). This is a cross-corpus benchmark, not a reproduction of XtraGPT's ReviseQA experiment.

## Artifact and licensing

- Model repository: [Xtra-Computing/XtraGPT-GGUF](https://huggingface.co/Xtra-Computing/XtraGPT-GGUF), pinned to repository commit `ebbce0efe4c726fd26df88237117367216ca42c6`.
- Selected file: `XtraGPT-1.5B-q4.gguf`, 1,646,573,088 bytes. Its Hugging Face linked ETag matches SHA-256 `45819cc88af6aa617a5a04fe29f783d74c38774b1052edcf94b8a1bec1c41293`.
- **Quantization discrepancy:** although the upstream basename contains `q4`, Ollama 0.30.11 parsed the artifact as `Q8_0`. ATEval reports the inspected tensor metadata (`Q8_0`) and preserves the original filename as provenance; it does not call this a Q4_K quantization.
- The model card declares MG0-2.0. The 1.5B model is based on Qwen2.5-1.5B-Instruct; its upstream model card declares Apache-2.0. The [XtraGPT card](https://huggingface.co/Xtra-Computing/XtraGPT-1.5B) says its training examples were derived from ICLR papers, but the source-text rights were not independently verified. Model checkpoint permission does not prove training-corpus permission.
- At the pinned GGUF repository revision, the official 1.5B files include the `q4`-named artifact and an F16/BF16 artifact. No publisher-hosted files were found for Q4_K_S, Q4_K_M, or Q5_K_M. A third-party conversion was not used.
- The BF16 file is 3,093,669,408 bytes. The GGUF model card labels 2B parameters while Ollama's imported architecture metadata reports 1.5B; the release/model naming and imported file metadata are therefore retained as separate observations.

## Runtime and limits

The machine reports 8 GB unified memory and Apple M1. PyTorch has no MPS backend in the project environment; Ollama detected Metal and reported 5.3 GiB available to that backend. XtraGPT ran with a 2,048-token context, temperature 0.1, seed 17, and a 128-token generation cap. Ollama's GGUF import path does not requantize the file. The model was not fine-tuned.

The official XtraGPT Transformers example uses `AutoTokenizer`, `AutoModelForCausalLM`, and `apply_chat_template`; the official prompt has `<PAPER_CONTENT>`, `<SELECTED_CONTENT>`, and `<QUESTION>` blocks. The ATEval GGUF runtime uses the model's Qwen chat markers and the same published block format. Its user-provided paper context is limited to the target sentence, adjacent source sentence context, and the section label. This is a bounded context proxy, not the full-paper context used in XtraGPT's intended workflow.

Ollama 0.30.11 loaded the checkpoint with Metal on the M1. The run recorded model-load, prompt-evaluation, and token-generation telemetry in the JSON report and per-example JSONL. CPU-only inference was not benchmarked separately. A 2,048-token context completed across the benchmark without silently truncating the input; the maximum prompt length actually observed is in the JSON metadata.

## Feasibility conclusion

The official GGUF artifact is feasible for short, local, review-required editing on this machine. The current deployment uses an Ollama loopback endpoint; it does not send manuscript text to a remote inference provider. The 3.09 GB BF16 weights and model runtime would leave less memory headroom, so BF16 was inspected but not run. Output latency is measured per request; the full run's observed peak runtime memory and generation rate are reported from the run rather than estimated from parameter count.

This evidence supports the 1.5B Q8_0 artifact as an executable prototype, not as a quality recommendation. The UI only exposes the model when the configured local Ollama tag is found by its live status check.

## References

- [XtraGPT 1.5B model card and Transformers inference contract](https://huggingface.co/Xtra-Computing/XtraGPT-1.5B)
- [Official XtraGPT GGUF collection and local-runtime instructions](https://huggingface.co/Xtra-Computing/XtraGPT-GGUF)
- [Official XtraGPT repository](https://github.com/Xtra-Computing/XtraGPT)
- [Ollama GGUF import documentation](https://github.com/ollama/ollama/blob/main/docs/import.mdx)
