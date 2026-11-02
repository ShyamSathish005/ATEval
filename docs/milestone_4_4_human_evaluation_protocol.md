# Milestone 4.4 human-evaluation protocol

## Preregistered design

The primary endpoints are: proportion better than the original, proportion
materially worse, material scientific-meaning change rate, unnecessary changes
on adjudicated no-edit passages, agreement with editing-necessity annotations,
false acceptance, and false rejection. Structural and claim-cue rejection
categories are analysed separately.

The isolated manifest is
[`evaluation_manifest.json`](../experiments/milestone4_4/evaluation_manifest.json).
It contains 30 diagnostic comparison items from M4.2 and 100 new necessity
items. The 30 items are not an independent test set. No reviewer ratings are
present at initialization.

## Blinding and assignment

The API returns only pseudonymous candidate labels and reviewer-specific,
seeded-randomized order. The model-to-label key is stored separately and is
never returned by the reviewer endpoint. Candidate positions are generated
from item and reviewer IDs to support counterbalancing. Reviewer identifiers
must be pseudonymous.

## Annotation

Reviewers rate editing necessity, candidate assessment, scientific meaning,
numeric accuracy, terminology, causal relationships, qualifications,
limitations, citations, technical correctness, comments, confidence, and
abstention. Multiple independent rows for the same item are allowed; duplicate
rows for one reviewer are rejected.

## Analysis

The analysis script reports weighted Cohen's kappa for paired ordinal
confidence ratings, preference proportions, and bootstrap confidence intervals
once real annotations exist. Multi-reviewer incomplete data should use
Krippendorff's alpha from a validated statistical implementation. Source
document clustering must be used for confirmatory bootstrap intervals.

No human responses are synthesized. Until qualified reviewers submit data, all
quality and reliability endpoints remain pending.
