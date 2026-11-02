# Milestone 4.1 generation benchmark

## Experiment

ATEval compared identity, the existing phrase-rule editor, and the official XtraGPT-1.5B GGUF generation on the unchanged IteraTeR-HUMAN document-grouped test manifest: **588 sentence pairs from 70 source documents**. Manifest and processed-file hashes are embedded in the run report. No train or validation data was added to the test split.

XtraGPT used the published `<PAPER_CONTENT>`, `<SELECTED_CONTENT>`, and `<QUESTION>` prompt blocks, wrapped in the Qwen chat format. The selected text and available neighboring source sentence context were provided. The gold IteraTeR edit-intention label was mapped to the corresponding instruction. This is oracle-conditioned and the evaluation corpus is not XtraGPT's ReviseQA benchmark; the result must not be described as a reproduction of the ACL paper's reported result.

Decoding was frozen at Ollama 0.30.11, context 2,048, temperature 0.1, seed 17, and at most 128 new tokens. Inference ran locally on the Apple M1 with Ollama's Metal backend. Per-example output and Ollama timing fields are in [`xtragpt_1_5b_q8_0_predictions.jsonl`](../reports/milestone4_1/xtragpt_1_5b_q8_0_predictions.jsonl); aggregate metrics, model checksum, runtime and manifest data are in [`xtragpt_1_5b_q8_0_benchmark.json`](../reports/milestone4_1/xtragpt_1_5b_q8_0_benchmark.json).

## Systems and status

| System | Result |
|---|---|
| Identity / no edit | Same held-out examples; copying baseline. |
| ATEval phrase rules | Same examples; conservative rule baseline. |
| XtraGPT-1.5B official GGUF | Local Q8_0 execution; publisher filename says `q4`, but runtime metadata says Q8_0. |
| IteraTeR BART / PEGASUS | Not run: each fine-tuned checkpoint needs an explicit model-specific license; base-model license alone is insufficient. |
| General instruction model | Not run: no separate local general instruction checkpoint was present. XtraGPT's Qwen lineage is not counted as an independent general-model comparator. |

The previous identity/rule results are archived in [`generation-baselines.json`](../reports/milestone4/generation-baselines.json). This run does not assert that XtraGPT is better. Human expert review has not yet occurred.

## Metrics and reading the results

The JSON reports add single-reference BLEU, ROUGE-L, SARI, token edit-operation precision/recall/F1, token edit-distance summaries, change rate, no-op overediting, and exact numeric/citation/protected-span sequence checks. BLEU, ROUGE-L and SARI are reference-overlap diagnostics. SARI was designed for simplification; the IteraTeR test contains mixed editing intents, so SARI is reported only as a diagnostic. BERTScore was not run because no local scorer checkpoint was installed. Fetching a second model solely for that metric would add a new model and provenance dependency.

None of the automatic metrics validates claim equivalence or academic quality. An exact numeric match can coexist with an invented interpretation, and a high overlap score can reward identity output. The human-readable preservation and failure reports describe these limits.

## Human review packet

The benchmark builds a 40-example offline blind-review packet stratified by available section labels. Each item presents the source and three pseudonymized alternatives (identity, phrase rules, XtraGPT); label order is shuffled per item. Reviewer choices, confidence and comments remain in the browser until exported. The answer key is a separate local file and is not embedded in the review page. Two qualified reviewers have not been recruited and no human ratings are included in these machine results.

## Reproducibility

The run configuration is in [`experiments/academic-generation-xtragpt-1_5b-v1.json`](../experiments/academic-generation-xtragpt-1_5b-v1.json), with the actual artifact checksum and exact runtime details in the benchmark JSON. Existing baseline output remains available, inference writes proposals rather than manuscript files, and the UI exposes model selection only when the configured local model is present.

## References

- [XtraGPT ACL 2026 paper](https://aclanthology.org/2026.acl-long.47/) and [official inference repository](https://github.com/Xtra-Computing/XtraGPT)
- [IteraTeR ACL 2022 paper](https://aclanthology.org/2022.acl-long.250/) and [original generator cards](https://huggingface.co/wanyu/IteraTeR-BART-Revision-Generator)
- BLEU: [Papineni et al., 2002](https://aclanthology.org/P02-1040/); ROUGE: [Lin, 2004](https://aclanthology.org/W04-1013/); SARI: [Xu et al., 2016](https://aclanthology.org/Q16-1029/); BERTScore: [Zhang et al., 2020](https://openreview.net/forum?id=SkeHuCVFDr)
