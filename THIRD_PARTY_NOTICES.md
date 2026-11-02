# Third-party notices

## IteraTeR-HUMAN dataset

The `data/raw/iterater_human_sent/` and `data/raw/iterater_human_doc/` exports are from the public IteraTeR-HUMAN dataset cards, which declare Apache-2.0:

- [Sentence dataset card](https://huggingface.co/datasets/wanyu/IteraTeR_human_sent)
- [Document dataset card](https://huggingface.co/datasets/wanyu/IteraTeR_human_doc)
- Source paper: [IteraTeR: Iterative Text Revision](https://aclanthology.org/2022.acl-long.250/)

The exact upstream file revisions and SHA-256 hashes are recorded in `data/manifests/`. IteraTeR Plus/v2 and IteraTeR-FULL are not included in this work. Review the source terms before redistributing the corpus or derived materials.

## DistilBERT encoder

The frozen encoder used for the contextual classification experiment is `distilbert/distilbert-base-uncased` at commit `12040accade4e8a0f71eabdb258fecc2e7e948be`; its [public model card](https://huggingface.co/distilbert/distilbert-base-uncased) declares Apache-2.0. The encoder weights are kept in the temporary Hugging Face cache and are not bundled here. A small scikit-learn logistic classification head is stored with experiment metadata under `models/revisions/iterater_distilbert_grouped_v1/`.

## Runtime dependencies

The Python optional dependency groups and exact versions are in `pyproject.toml`; they install upstream packages from their package indexes. Their transitive licenses and security advisories must be reviewed using the release SBOM and vulnerability audit. Package license compatibility has not yet been completely audited.

The frontend lockfile identifies exact npm dependencies. Direct packages
verified from installed upstream package metadata include Poppins fonts
(OFL-1.1), React/React DOM, Radix UI icons, Motion, Recharts, Tailwind CSS,
and Vite (MIT), and TypeScript (Apache-2.0). Preserve the upstream notices
when redistributing built font or package assets. Review all transitive
packages with the release SBOM before publication.

The design exploration image at `frontend/public/design-option-3.png` has
unverified provenance, is not used by the application UI, and is excluded
from release artifacts pending ownership review.

No external service is used by default at application runtime; explicit model
download or optional inference configuration is required for model-backed
experiments.

Other external research repositories remain references only. Their code, data, and model licenses must be inspected independently before reuse or download. In particular, Turnitout-Humanizer is identified as proprietary by the supplied project brief; no code or rules from it are included or reverse engineered.
