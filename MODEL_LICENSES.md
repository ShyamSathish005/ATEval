# Model licenses and distribution status

ATEval does not own third-party model weights. No generation checkpoint is
downloaded automatically or included in the local application Docker image.
Users who opt into model inference must obtain the exact checkpoint, inspect
its current license and acceptable-use terms, and satisfy any base-model terms.

| Model | Upstream status checked 2026-11-02 | ATEval handling |
|---|---|---|
| `distilbert/distilbert-base-uncased` at `12040accade4e8a0f71eabdb258fecc2e7e948be` | Hugging Face model card declares Apache-2.0. The checkpoint is not bundled. | Optional comparison only. Its derived classifier heads are excluded pending dataset-derived-artifact review. |
| [XtraGPT-1.5B](https://huggingface.co/Xtra-Computing/XtraGPT-1.5B) | Model card declares ModelGo Zero License 2.0; card identifies Qwen2.5-1.5B-Instruct as a base. [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) has an Apache-2.0 model card. | Not bundled or downloaded. Review the exact XtraGPT and base model license files, tokenizer, and applicable terms at the selected revision before redistribution. |
| XtraGPT-3B, 7B, 14B | Collection/checkpoint pages expose the relevant model cards; status may vary by revision. | Not bundled. Do not infer license from another size. Verify the exact checkpoint and base model independently. |
| IteraTeR BART / PEGASUS revision generators | Exact checkpoint license metadata and the underlying IteraTeR-FULL material have not been verified for this release. | Not bundled. Do not download from ATEval automatically. |
| Ollama models or user-supplied checkpoints | User-selected distribution and model terms. | User-managed; ATEval does not distribute weights or proxy manuscript content to a hosted model service. |

Model license claims are based on the upstream cards, not on rights to their
training corpora or outputs. Verify current files and revision-specific terms
before use. This table is an inventory, not legal advice.
