# Implementation audit

**Audit date:** 2026-11-01 (Asia/Kolkata)
**Workspace inspected:** ATEval project directory

## Actual starter state

The project directory was empty: it contained no source files, tests, dependency manifests, README, or `academic-text-eval-v0.1.zip`. Consequently there was no existing Python implementation to inspect, no dependency versions to audit, and no pre-existing tests to run. This audit does not infer or invent prototype behavior. The workspace has now been initialized with a small, dependency-free foundation in response to the prompt's fallback instruction.

The parent Git root is the Desktop, which contains unrelated user material. No Git-wide status cleanup, staging, commit, or repository configuration change was performed.

## Existing functionality observed

Before this work: none was present in this project directory.

After this foundation pass:

- `ateval` CLI provides `doctor`, `detector list`, `papers audit`, and `version` commands.
- TOML configuration validates a small set of runtime settings; offline mode defaults to true.
- Dataset records preserve mandatory source/label/dataset identity and optional generator, domain, language, split, and metadata.
- Detector and model registries mark planned algorithms explicitly as planned/not configured.
- Logs can be emitted as JSON; the code does not log document bodies.

## Defects and fragile assumptions

There was no starter code to evaluate for defects. The new foundation is intentionally narrow. Known limitations in this foundation are:

- The CLI is built on `argparse`; richer command coverage and uniform exit-code policy remain future work.
- `papers audit` currently points to the human-reviewed registry document and is not yet a machine-verifying citation audit.
- Dataset schema validation is record-level only. It does not yet validate label provenance, duplicate IDs, split leakage, hashes, schema versions, or dataset licence terms.
- The doctor command detects optional packages and LaTeX executables but does not inspect model caches, disk capacity, memory, accelerator availability, package versions, or compiler safety settings.
- There is no experiment runner, metrics implementation, LaTeX parser, or detector calculation yet.

## Dependencies and licensing

The runtime currently imports only the Python standard library and requires Python >=3.11 for `tomllib`. Build isolation requests setuptools >=68. No model packages are forced, and no downloads occur. Exact installed versions were not inferred because no project environment or lockfile existed. A pinned lock/export, SBOM, and automated licence inventory are still needed before a research release.

No external code/data/assets are bundled. The project brief states that the Turnitout-Humanizer repository is proprietary; this implementation contains no copied code or rules. Third-party Notices records the current state.

## Security and privacy concerns

- No automatic API calls, telemetry, model downloads, or manuscript persistence are implemented.
- Avoid passing document contents into routine log messages. Current CLI commands only log generic status.
- Future LaTeX validation must not enable shell escape or execute arbitrary TeX commands.
- Model and dataset downloads will need explicit opt-in, source/revision recording, licence review, and integrity checks.
- User-controlled paths and archive inputs will need validation when file-reading commands are added.

## Research and implementation gaps

The highest-priority missing work is: a verified machine-readable paper registry; dataset adapters and provenance checks; baseline metrics and scoring; train/test leakage controls; paired academic-domain data; low-FPR operating metrics and uncertainty intervals; reproducibility manifests; fairness analysis with ethically obtained subgroup labels; robust LaTeX traversal/protection; and evaluation reports.

The methods DetectGPT, Fast-DetectGPT, Binoculars, TempTest, KGW watermarking, and SynthID-Text are not implemented. Their registry entries are planning metadata only. No benchmark result or reproduction claim exists.

## Tests executed

There were no tests to run before scaffolding. After adding the foundation, `python -m unittest discover -s tests -v` was run and passed all 6 tests (configuration defaults/loading, schema preservation/validation, registry honesty, CLI list and doctor). This is foundation verification, not an algorithm reproduction test suite.

## Architecture and development sequence

See the architecture diagram in the project README. Recommended next steps: (1) replace the paper prose file with a verified structured registry and audit command; (2) add dataset manifests and integrity/leakage validators; (3) implement metric functions before detector scoring; (4) add transparent statistical baselines; (5) add exact model-backed algorithms one at a time against their primary papers and reference repositories; (6) build academic-domain and fairness experiments; (7) develop a separate academic quality/LaTeX protection subsystem; (8) release only after independent reproduction and licence review.
