# Detector dataset and provenance plan

## Required labels

The detector benchmark must contain document- and author-grouped examples of:

- genuinely human-authored academic prose;
- model-generated academic prose from multiple model families;
- human-edited machine-generated prose;
- mixed-authorship documents and difficult borderline passages where available.

Each record must retain source document, author/group identifier, domain,
section, generation model/revision, edit history, licence, acquisition
provenance, and label confidence.

## Current audit

| Asset | Available in repository | Valid detector label? | Licence/provenance |
|---|---:|---:|---|
| IteraTeR-HUMAN revisions | Referenced/optional | **No**: revision-intent labels, not authorship labels | Apache-2.0 card; source/derived review required |
| XtraGPT predictions | Historical experiment artifacts | **No**: generated outputs lack matched human authorship benchmark | Model and source terms are separate |
| Local academic writing data | Not bundled | No | Must be acquired under explicit terms |
| Human-evaluation packets | Reviewer infrastructure | No labels collected | Excerpts/consent and redistribution require review |

No detector training data or benchmark labels are fabricated by M5.
Until a licensed, document-grouped corpus is acquired, detector metrics,
calibration, cross-model generalisation, and threshold claims remain pending.
