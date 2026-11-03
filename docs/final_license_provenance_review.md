# Final licence and provenance review

**Review date:** 2026-11-03
**Scope:** Public repository state at merged main commit
`bbfa15936ecf3b092cf0ef2f99a33ad6c0ecc270`.

## Owner confirmation

On 2026-11-03, the project owner explicitly confirmed in the release
preparation record that they are the true owner of the ATEval project and have
authority to license the project-authored portions under MIT. This confirmation
resolves the project-owner authority gate for those portions.

The confirmation does not transfer ownership of third-party dependencies,
fonts, models, datasets, source passages, or other external assets. Those
materials remain subject to their own licences and provenance requirements.

## Finding: historical provenance is limited

The repository contains an MIT `LICENSE` with the notice `Copyright (c) 2026 ATEval contributors`. The available Git history has five commits, all attributed to `ShyamSathish005 <shyamsathish10@gmail.com>`. However, the history begins with an imported/squashed project snapshot (`794b3af`, “Import ATEval as standalone project”); it does not preserve the source workspace's complete file history or establish who originally authored every imported file.

Git author metadata records commit attribution, not copyright title or an assignment. The historical record does not independently establish file-level authorship or
external contributor assignments. The owner confirmation above is the
authority basis for the project-authored release scope; it does not extend to
external materials. The broad “ATEval contributors” copyright line is retained
without modification.

Before a formal release, the project owner should confirm authorship or permission for the files they contributed, identify any contributors whose rights are not assigned, and confirm authority to apply MIT to the project-authored portions. If that cannot be confirmed, obtain the necessary permissions and/or revise the release scope and copyright notice. This is an unresolved owner-confirmation item, not a claim that the project lacks authority.

The explicit owner declaration was supplied for this review. No copyright
notice was modified.

## Provenance categories

The release review distinguishes the following categories:

- **Project-authored code:** `ateval/`, `scripts/`, tests, configuration, and
  project documentation are treated as project-authored material for release
  scoping, but ownership authority remains owner-confirmation pending because
  the repository was imported as a snapshot.
- **AI-assisted development:** some development work may have used AI
  assistance. Assistance does not by itself transfer copyright or establish
  authorship; generated or modified files remain subject to the same review.
- **Third-party contributions:** no contributor assignment or licence grant is
  recorded in this repository beyond the single visible Git author identity.
- **Third-party dependencies:** Python and npm packages, GitHub Actions,
  fonts, and other upstream components retain their upstream licences. They
  are not project-owned.
- **Models and datasets:** model checkpoints, research corpora, source
  passages, and derived research artifacts are not project-owned, are not
  bundled in the release, and require revision-specific upstream review.

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

The existing MIT text, `NOTICE`, and third-party notices were retained. The
archive allowlist excludes the unverified design image and all raw data, model,
report, experiment, and generated output directories.

This report does not offer legal advice or make a final rights determination.
MIT is retained for the portions the owner is authorized to license; this
report does not extend MIT to external assets. The project must not be
represented as having cleared rights for external materials. Project-owner
authority for project-authored material is confirmed, but no formal release is
authorized by this review while the remaining operational gates are open.
