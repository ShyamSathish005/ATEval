# Final licence and provenance review

**Review date:** 2026-11-02  
**Scope:** Public repository state at `38db980` plus the M0.2 changes in this branch.

## Finding: release authority is not established

The repository contains an MIT `LICENSE` with the notice `Copyright (c) 2026 ATEval contributors`. The available Git history has five commits, all attributed to `ShyamSathish005 <shyamsathish10@gmail.com>`. However, the history begins with an imported/squashed project snapshot (`794b3af`, “Import ATEval as standalone project”); it does not preserve the source workspace's complete file history or establish who originally authored every imported file.

Git author metadata records commit attribution, not copyright title or an assignment. The current records therefore do not establish that the named project owner wrote or owns every project file, that any external contributors assigned their rights, or that the project owner has authority to offer all project-authored material under MIT. The broad “ATEval contributors” copyright line is not substantiated by the available repository history. It has **not** been changed automatically.

Before a formal release, the project owner should confirm authorship or permission for the files they contributed, identify any contributors whose rights are not assigned, and confirm authority to apply MIT to the project-authored portions. If that cannot be confirmed, obtain the necessary permissions and/or revise the release scope and copyright notice. This is an unresolved owner-confirmation item, not a claim that the project lacks authority.

## File provenance evidence

- The five visible commits and current tracked project files are attributable in Git to one committer identity. This is the only authorship evidence available in the standalone repository.
- The initial import commit is a snapshot, so file-level historical provenance cannot be reconstructed from this repository alone. No claim is made here that each file was written solely by the recorded committer.
- The repository does not contain a vendored `node_modules` tree or vendored Python dependency source. Python and JavaScript libraries are installed from upstream package registries and are third-party components rather than project-owned code.
- GitHub Actions are referenced by workflow tags and are not copied into the repository.
- No model checkpoints or raw research corpus are included in the public source tree. They are deliberately excluded by the archive and Docker configuration.
- The frontend uses the Poppins webfont through `@fontsource/poppins`; the package declares the font's OFL-1.1 terms. Preserve the font licence and notices when redistributing built assets.
- `THIRD_PARTY_NOTICES.md` identifies the IteraTeR-HUMAN dataset and DistilBERT model, and records that the dataset source passages and fitted artifacts need separate provenance review. `MODEL_LICENSES.md` and `DATASET_LICENSES.md` state that model weights and research corpora are not bundled and require revision-specific upstream review.
- The design exploration image `frontend/public/design-option-3.png` has unverified provenance. It is unused by the application and is excluded from release archives; do not redistribute it until provenance is established.
- Runtime and frontend dependency licences are not fully inventoried in the existing notice. The dependency audit and SBOM can enumerate resolved packages but do not themselves grant permission or prove licence compatibility.

## Current notices and actions

The existing MIT text, `NOTICE`, and third-party notices were retained. `NOTICE` already says contributor ownership and release authority have not been verified. The archive allowlist excludes the unverified design image and all raw data, model, report, experiment, and generated output directories.

This report does not offer legal advice or make a final rights determination. The MIT licence may remain in the repository as historical project state, but the project must not be represented as having cleared contributor authority until the project owner confirms the necessary rights. No formal release is authorized by this review.
