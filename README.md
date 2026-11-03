<div align="center">
  <img src="docs/assets/ateval-hero.svg" alt="ATEval: manuscript signals flowing through analysis, protected revision, and author review" width="100%">

  <h1>ATEval</h1>
  <p><strong>Academic Text Evaluation &amp; Writing Intelligence</strong></p>
  <p>Local-first research infrastructure for understanding, revising, and evaluating academic writing without treating language signals as proof of authorship.</p>

  <p>
    <a href="docs/installation.md"><img src="https://img.shields.io/badge/GET%20STARTED-installation-0ea5a8?style=flat-square" alt="Get started"></a>
    <a href="docs/architecture.md"><img src="https://img.shields.io/badge/DOCUMENTATION-architecture-2563eb?style=flat-square" alt="Architecture documentation"></a>
    <a href="docs/RESEARCH.md"><img src="https://img.shields.io/badge/RESEARCH-methodology-4f46e5?style=flat-square" alt="Research documentation"></a>
    <a href="docs/EVALUATION.md"><img src="https://img.shields.io/badge/EVALUATION-results-7c3aed?style=flat-square" alt="Evaluation documentation"></a>
    <a href="docs/ROADMAP.md"><img src="https://img.shields.io/badge/ROADMAP-next-64748b?style=flat-square" alt="Roadmap"></a>
  </p>
  <p>
    <a href="https://github.com/ShyamSathish005/ATEval/actions/workflows/ci.yml"><img src="https://github.com/ShyamSathish005/ATEval/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status"></a>
    <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776ab?style=flat-square&logo=python&logoColor=white" alt="Supported CI Python versions">
    <img src="https://img.shields.io/badge/status-alpha%20research%20preview-f59e0b?style=flat-square" alt="Alpha research preview">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-16a34a?style=flat-square" alt="MIT license for project-authored material"></a>
  </p>
</div>

> **Research status:** ATEval is experimental, not production-ready or scientifically validated. Revision suggestions require author review. It now includes an uncalibrated stylometric research signal, not an authorship detector, and must not be used to make authorship, misconduct, or academic-integrity determinations.

## What ATEval is

ATEval investigates the difference between **rewriting text** and **revising academic writing responsibly**. It combines manuscript ingestion, source mapping, descriptive analysis, revision-intention experiments, protected-content checks, selective revision prototypes, and author-controlled review in a local-first workspace.

The design priorities are:

- preserve technical meaning, numbers, citations, terminology, and document structure;
- make revision intent explicit before proposing a change;
- abstain when automated checks cannot establish safety;
- keep datasets, model checkpoints, prompts, hashes, and evaluation splits reproducible;
- separate research infrastructure from claims about writing quality or authorship.

## Navigation

| Start | Understand | Research | Project |
|---|---|---|---|
| [Installation](docs/installation.md) · [Quick start](docs/quick_start.md) | [Architecture](docs/architecture.md) · [Limitations](docs/known_limitations.md) | [Research](docs/RESEARCH.md) · [Evaluation](docs/EVALUATION.md) | [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) |
| [Troubleshooting](docs/troubleshooting.md) · [OS notes](docs/os_installation.md) | [Privacy](PRIVACY.md) · [Data handling](docs/DATASETS_AND_LICENSING.md) | [Benchmarks](docs/revision_benchmark_report.md) · [SCAR](docs/scar_algorithm_specification.md) | [Roadmap](docs/ROADMAP.md) · [Changelog](CHANGELOG.md) |

## Capability matrix

| Capability | Status | Evidence and boundary |
|---|---|---|
| Local CLI, API, and React workspace | **Available** | `ateval/`, `frontend/`, and the tested CI workflow |
| `.txt` and `.tex` manuscript ingestion | **Available** | Source-mapped local analysis; no TeX compilation |
| LaTeX project ZIP ingestion | **Available** | Validated archive paths and preserved project assets |
| DOCX and text-layer PDF ingestion | **Experimental** | Optional document dependencies; PDF output is read-only |
| Descriptive academic-writing analysis | **Available** | Linguistic signals only; not authorship evidence |
| Revision-intention classifier | **Experimental** | Grouped baselines are advisory and weak on rare classes |
| SCAR selective revision pipeline | **Experimental** | Protected spans, fail-closed checks, and author approval required |
| Model-backed generation | **Experimental** | User-managed local model/runtime; no weights bundled |
| Human-evaluation workflow | **Infrastructure available** | Blinded packet and annotation tooling exist; qualified outcomes remain pending |
| AI-writing evaluator baseline | **Experimental** | Deterministic stylometric signal; no calibration, benchmark, or authorship conclusion |
| Public confidential-manuscript service | **Not offered** | Local loopback workflow only; review [privacy](PRIVACY.md) |

## Quick start

Requires Python 3.11 or newer. The base install does not download models or datasets.

```sh
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m ateval doctor
python -m ateval --help
```

For the local UI and document extraction:

```sh
python -m pip install -e ".[ui-server,writing-docs]"
cd frontend && npm ci && npm run build
cd ..
python -m ateval api
```

Open `http://127.0.0.1:8000` after the production build. Development mode uses `cd frontend && npm run dev` and proxies `/api` to the loopback API. See [installation](docs/installation.md) for Docker Compose and optional research extras.

Analyze a manuscript without overwriting its source:

```sh
python -m ateval writing analyze paper.tex --output paper-review.json
```

## System architecture

```mermaid
flowchart LR
  Input[Manuscript input] --> Parse[Parser and source maps]
  Parse --> Signals[Descriptive analysis]
  Parse --> Protect[Protected content]
  Signals --> Intent[Author-intent proposal]
  Protect --> Gate[Fail-closed validation]
  Intent --> Gate
  Gate --> Review[Author review]
  Review --> Export[Reviewed export and audit]
  API[Loopback FastAPI] --> Parse
  State[(SQLite metadata)] --> API
```

ATEval reads uploads locally, builds in-memory projections, and stores local metadata under `.ateval/`. Optional model inference is explicitly user-managed. It does not execute document shell commands, compile LaTeX, or prove semantic equivalence. See the [architecture guide](docs/architecture.md).

## Research and evaluation

ATEval treats revision as a constrained, reviewable research problem rather than arbitrary paraphrasing. The repository includes literature reviews, document-grouped IteraTeR-HUMAN experiments, SCAR gate analysis, protected-span regression tests, failure analysis, and blinded human-evaluation infrastructure.

Results are deliberately qualified:

- XtraGPT local inference is documented as an experimental generator, not a safe automatic editor.
- BLEU, ROUGE, edit rate, and classifier metrics are overlap or diagnostic measurements, not proof of better academic writing.
- Automated structural checks do not establish semantic equivalence.
- M4.4 provides reviewer infrastructure, but no simulated reviewer responses are presented as evidence.

Read [Research & Evaluation](docs/RESEARCH.md), [evaluation details](docs/EVALUATION.md), and the [research methodology](docs/research_methodology.md) before interpreting any result.

## Data, licensing, and privacy

Project-authored material is released under MIT according to the owner's recorded confirmation. Dependencies, fonts, model checkpoints, datasets, source passages, and derived research artifacts retain their own licences and are not implicitly covered by MIT. See [datasets and licensing](docs/DATASETS_AND_LICENSING.md), [model licences](MODEL_LICENSES.md), and [privacy](PRIVACY.md).

The default workflow binds to loopback. Do not send unpublished manuscripts to a remote model or hosted deployment without an independent privacy review. Raw research data and generated experiment outputs are excluded from release archives.

## Release status

The current branch is an alpha research preview. Main CI run
[`41573865780`](https://github.com/ShyamSathish005/ATEval/actions/runs/41573865780)
passes Python 3.11–3.13, frontend checks, dependency audits, archive hygiene,
and the Docker image build. Docker Compose runtime verification, complete
cross-platform installation evidence, and independent security/privacy review
remain release gates. See the [release checklist](docs/release_checklist.md)
and [readiness report](docs/release_readiness_report.md).

## Contributing and citation

Contributions should preserve provenance, reproducibility, and the distinction between descriptive signals and scientific claims. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Citation metadata is available in [CITATION.cff](CITATION.cff).
