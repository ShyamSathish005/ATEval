# Extended academic revision research

**Reviewed:** 2026-11-01  
**Scope:** XtraGPT, Re3-Sci2.0, CASIMIR, EditEval, and reproducible generation baselines  
**Decision:** prioritize a locally wrapped published academic editor (XtraGPT 1.5B) once model weights are available; do not start alternative fine-tuning until data rights and a human-evaluation protocol are resolved.

## Executive summary

XtraGPT is the closest published match to ATEval's next objective: instruction-conditioned academic revision grounded in wider paper context, section criteria, and human review. Its 1.5B/3B/7B/14B checkpoints are released under MG0-2.0 according to the repository/model cards, but model licenses do not settle the rights in the 140,000-pair ReviseQA corpus or in all base-model lineage. The repository's inference recipe expects an instruction plus `<PAPER_CONTENT>`, `<SELECTED_CONTENT>`, and `<QUESTION>` fields. On this machine, 8 GB unified memory, CPU-only Python environment without installed Transformers/PyTorch, and no locally available model service make the 1.5B checkpoint a possible quantized follow-up but not a credible immediate full-precision benchmark; 3B and larger are outside the present budget.

Re3-Sci2.0 adds scientific-document edit annotations and is suitable for non-commercial research only under its stated CC BY-NC 4.0 terms. It is not cleared for commercial model training or distribution. CASIMIR is a valuable large scientific revision resource with sentence alignments and paragraph positions; its Hugging Face card says MIT, while the source articles and revisions derive from OpenReview and must be licensed independently. EditEval provides useful instruction-following and fluency/clarity/coherence comparison tasks, but it mixes task genres and source datasets; use its IteraTeR fluency, clarity, and coherence slices as auxiliary editing checks, not as a substitute for science-specific human review.

## A. XtraGPT

### Method and scope

XtraGPT introduces an academic-writing human-AI revision workflow with criteria-guided intent alignment and context-aware editing. The ACL 2026 paper reports ReviseQA: 7,000 ICLR 2024 papers and 140,000 instruction–revision pairs, with a held-out set organized by papers. Its section criteria cover six areas (title, abstract, introduction, background, evaluation, conclusion); three PhD evaluators rated instruction following, criteria alignment, in-context reference, and revision acceptance on a sample. The paper's approach is a more suitable *published baseline* than using a general chat model as a proxy for academic revision.

The paper and official repo describe a 1.5B–14B family. Published base-model lineage is Qwen2.5-1.5B-Instruct (XtraGPT-1.5B), Llama-3.2-3B-Instruct (3B), Qwen2.5-7B-Instruct (7B), and Phi-4 (14B). Official code fine-tunes with LLaMA-Factory and reports learning rate 1e-6, four epochs, per-device batch size 1, gradient accumulation 4, 16,384 token maximum sequence length, and warmup ratio 0.1. Training those settings is not realistic on this workstation; the immediate path is inference only.

### Inference method and resource fit

The official Transformers recipe loads `AutoTokenizer` and `AutoModelForCausalLM`, formats chat input with the model's chat template, and generates from the resulting prompt. The paper/repository prompt supplies the paper context, selected content, and an editing question. The example generation setting is temperature 0.1 and a maximum 16,384 new tokens; that output limit is far more than ATEval needs. For ATEval, cap input to the selected paragraph plus nearby section context, cap output around 512 new tokens, set deterministic decoding, and reject malformed/empty outputs. The repository also documents vLLM with a 16K context; vLLM targets supported GPU deployments, and is not an Apple CPU substitute.

Inference storage is approximately parameter-count × bytes/parameter before runtime, activations, and KV cache. At FP16, rough weight-only estimates are 3 GB for 1.5B, 6 GB for 3B, 14 GB for 7B, and 28 GB for 14B. With only 8 GB unified memory, 1.5B full precision is marginal; 3B full precision leaves insufficient headroom; 7B and 14B exceed machine capacity. Quantization may permit 1.5B locally through a compatible GGUF/Ollama route, but no model is installed here and the Ollama local server was unavailable. Actual generation speed and memory must be measured on the target deployment rather than inferred from parameter count. XtraGPT identifies the upstream bases as [Qwen2.5-1.5B (Apache-2.0)](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct), [Llama-3.2-3B (Meta Llama 3.2 license)](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct), [Qwen2.5-7B (Apache-2.0)](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct), and [Phi-4 (MIT)](https://huggingface.co/microsoft/phi-4). Those terms are independent of the XtraGPT checkpoint declaration.

### License and data provenance

- The XtraGPT cards and repository declare MG0-2.0 for model checkpoints. Model-card base lineage is independently relevant: Qwen2.5-1.5B is Apache-2.0; the 3B lineage uses Meta's Llama 3.2 license; 7B follows Qwen2.5; 14B follows Phi-4. Review the exact checkpoint card, upstream base terms, and model release license for the intended distribution/use before release.
- ReviseQA is described as 7,000 papers collected from ICLR 2024 via OpenReview and used to create instruction–revision pairs. The ACL paper does not state a blanket text-dataset license in the sections reviewed. A permissive model-card license does **not** license those source papers or the dataset. Do not redistribute ReviseQA text or train an ATEval model on it until the actual dataset card and source-paper terms have been independently verified for that use.
- The repository offers a ReviseQA Hugging Face dataset. The corpus can be investigated first through metadata and a small, license-reviewed sample; no full corpus was added to ATEval in this milestone.

### ATEval decision

Use the authors' recommended `<PAPER_CONTENT>`, `<SELECTED_CONTENT>`, and `<QUESTION>` scheme as the starting inference contract. The ATEval adapter adds preservation constraints (protected terms/citations/numbers/LaTeX), structured rationale/risk output, reversible proposals, and abstention for uncertain changes. This prompt mode is an ATEval adaptation, not an exact replication of the published evaluation: the paper's held-out ReviseQA benchmark is 350 held-out ICLR papers with 7,000 QA pairs, and its method supplies full-paper context. The current adapter accepts bounded local paragraph/neighbor context and the existing M3 split is IteraTeR-HUMAN. Reproducing the paper's reported XtraGPT baseline requires the official ReviseQA test data, exact prompt/config, and a licensed checkpoint. The adapter is not a new model checkpoint and must be reported as “XtraGPT via ATEval constraints,” not as an ATEval-trained model.

## B. Re3-Sci2.0

The EMNLP 2024 work reports 1,780 scientific document revisions and more than 94,000 labeled edits; the authors created Re3-Sci2.0 using their best-performing edit-intent classifier and assessed quality with human evaluation. Thus the dataset is useful for studying human-edit distributions and edit-intent behavior, but the labels are partly model-generated and are not equivalent to sentence-by-sentence expert annotations. It is not, from the paper abstract alone, a ready-made source/revised generation benchmark with independent human target text for every row; inspect the package schema before selecting a generation split.

The TU Darmstadt dataset record states **CC BY-NC 4.0 unless otherwise noted**. This forbids assuming the data is cleared for commercial training or distribution. ATEval may stage a research-only, provenance-tracked local inspection if needed, but must keep the resource separate from commercial training, product model weights, or shipped packages unless additional rights are obtained. Attribute the source and preserve per-item exceptions. The record is accessible at the [dataset landing record](https://tudatalib.ulb.tu-darmstadt.de/items/469ec002-60a1-4fa7-8183-e783ad9a81ff); the published paper and author implementation are linked below.

## C. CASIMIR

CASIMIR contains multiple revised versions of 15,646 scientific articles from OpenReview and their peer reviews. Consecutive versions are aligned at sentence level with paragraph-location metadata; edits and revision intentions are automatically extracted. The corpus is suitable for paragraph-context, position-aware alignment, terminology-consistency, and discourse-level experiments. The CASIMIR authors themselves question the relevance of current automatic evaluation metrics for revision, reinforcing the need for expert review.

The [Hugging Face dataset card](https://huggingface.co/datasets/taln-ls2n/CASIMIR) declares MIT for the *dataset repository/derived artifact*. The card's rows contain text from OpenReview papers and reviews, whose source-specific rights and OpenReview terms are a separate question. MIT in the dataset viewer is not proof that every included paper/review is relicensed by its author. Before ingestion, record both repository license and source-document license/permissions. The full corpus is large (the viewer indicates 10M–100M rows) and should be filtered to document-disjoint, rights-cleared subsets before local experiments.

## D. EditEval

EditEval is an instruction-based benchmark for seven kinds of editing: fluency, clarity, coherence, paraphrasing, simplification, neutralization, and updating. It includes IteraTeR fluency/clarity/coherence slices, JFLEG, STS-B MultiMT, Turk/ASSET, WNC, FRUIT, and Wafer-Insert. Its authors warn that common editing metrics do not always agree and that an instruction prompt that works for one model may not transfer to another. The repository was archived read-only in 2023.

For ATEval, the IteraTeR fluency, clarity, and coherence subsets can support controlled auxiliary comparisons. The task source should still be checked at the dataset level because the underlying IteraTeR corpora include multiple domains, not just scientific prose. The remaining slices measure useful generic editing capabilities but do not test scientific claim preservation, citation integrity, methods/results precision, or argument correctness. The benchmark repository is CC0 for code; the original EditEval paper/dataset release identifies CC BY-NC-SA 4.0. Individual upstream datasets may have additional terms. Do not assume repository code permission licenses all benchmark text.

## Generation benchmark plan and current evidence

All model systems must run against the **same held-out document groups and examples**, with the same request context and instruction where possible. Keep a generation run manifest recording checkpoint ID/revision, checkpoint license, base lineage/license, a separate training-data provenance/license note, decoding parameters, software versions, hardware, prompt hash, truncation, output hashes, and failures. Do not use Re3-Sci2.0 for commercial product training or distribute its text.

| System | Status | Conditions / blockers |
|---|---|---|
| Identity / no-edit | **Run in M3** | 588 held-out examples / 70 documents; BLEU 0.7921, ROUGE-L 0.8665, edit-operation F1 0; structural spans preserved. Overlap scores mostly reward copying; no quality judgment. |
| Current ATEval phrase rules | **Run in M3** | Same examples; 0.68% changed, edit-operation F1 0.00129; no demonstrated quality gain. |
| IteraTeR BART | **Runner implemented; not run** | Fine-tuned on IteraTeR-FULL. Official protocol uses `AutoModelForSeq2SeqLM`, `<intent> original sentence`, `num_beams=8`, and `max_length=1024`; runner is sentence-only. The fine-tuned checkpoint card does not declare its own license. Base BART license cannot be substituted for that missing checkpoint grant. Obtain clarification before weights are downloaded/used. |
| IteraTeR PEGASUS | **Runner implemented; not run** | Same official intent prefix and generation settings; fine-tuned on IteraTeR-FULL. No explicit fine-tuned checkpoint license on its card. Base PEGASUS license does not independently license the fine-tuned checkpoint/data. |
| XtraGPT 1.5B / 3B | **Not run** | Checkpoint card says MG0-2.0; training-paper text rights need verification. This host has 8 GB unified memory, no MPS/CUDA, no installed Transformers/PyTorch in the project environment, no local XtraGPT files, and no running Ollama service. 1.5B quantized may fit later; 3B FP16 is not practical here. First reproduce against the official ReviseQA held-out papers when data rights and hardware permit; an IteraTeR-HUMAN run would be a separate cross-dataset benchmark. |
| General instruction-following model | **Runner implemented; not run** | A generic local Transformers chat-model adapter is available; Qwen2.5-1.5B-Instruct is a suitable Apache-2.0 base checkpoint candidate. No local instruction model is installed. A remote API would transmit manuscript text and change the local-only privacy boundary, so it is not used as an unapproved fallback. |
| ATEval constrained XtraGPT adapter | **Implemented as an optional local adapter; not run** | Uses the published XtraGPT input contract and ATEval protection/structured review requirements. It is not an independently trained ATEval model. |

Identity and rule scores were reproduced on the verified M3 grouped test and saved in [`reports/milestone4/generation-baselines.json`](../reports/milestone4/generation-baselines.json). This report does not claim a neural generation result or an improvement in writing quality. BLEU, ROUGE, edit overlap, and exact protected-span checks are diagnostics, not substitutes for human semantic and clarity ratings.

### Required next benchmark work

1. Obtain explicit rights guidance for the IteraTeR fine-tuned BART/PEGASUS weights and verify all upstream dataset terms.
2. First reproduce the official XtraGPT-1.5B result on its ReviseQA held-out paper set using the authors' full-paper prompt, split, and evaluation procedure, once data rights and suitable hardware are verified. Separately run XtraGPT-1.5B on the ATEval grouped IteraTeR-HUMAN test with the published prompt mode and the ATEval-constrained prompt as cross-corpus experiments. Evaluate XtraGPT 3B only on a machine with sufficient memory after 1.5B validation.
3. Add a local general instruction-following comparator only after model and corpus rights review; keep it distinct from an academic-revision-specific checkpoint.
4. Add output-level validation and blinded reviewer packets. Have academic reviewers assess grammar, clarity, appropriateness, technical accuracy, meaning, paragraph coherence, preference, and whether no change is preferable. Report reviewer count, inter-rater agreement, document-cluster uncertainty, and disagreements.
5. Revisit training only after secure, permissive, generation-pair data is documented. Keep all NC data out of any commercial training path.

## Sources

- [XtraGPT ACL 2026 paper](https://aclanthology.org/2026.acl-long.47/), [official repository](https://github.com/Xtra-Computing/XtraGPT), [model collection](https://huggingface.co/collections/Xtra-Computing/xtragpt), and [1.5B model card](https://huggingface.co/Xtra-Computing/XtraGPT-1.5B).
- [Re3-Sci2.0 EMNLP 2024 paper](https://aclanthology.org/2024.emnlp-main.839/), [TUDa dataset record](https://tudatalib.ulb.tu-darmstadt.de/items/469ec002-60a1-4fa7-8183-e783ad9a81ff), [author code](https://github.com/UKPLab/emnlp2024-llm-classifier).
- [CASIMIR LREC-COLING 2024 paper](https://aclanthology.org/2024.lrec-main.257/) and [dataset card](https://huggingface.co/datasets/taln-ls2n/CASIMIR).
- [EditEval CoNLL 2024 paper](https://aclanthology.org/2024.conll-1.7/) and [archived official code/data repository](https://github.com/facebookresearch/EditEval).
- [IteraTeR ACL 2022 paper](https://aclanthology.org/2022.acl-long.250/), [official repository](https://github.com/vipulraheja/iterater), [BART card](https://huggingface.co/wanyu/IteraTeR-BART-Revision-Generator), and [PEGASUS card](https://huggingface.co/wanyu/IteraTeR-PEGASUS-Revision-Generator).
