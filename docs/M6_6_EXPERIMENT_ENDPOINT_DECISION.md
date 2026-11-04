# M6.6 Experiment Execution Endpoint Decision (`BUG-01`)

**Endpoint:** `POST /api/v1/experiments/{experiment_id}/run`  
**Decision:** **Option B — Disabled by default; available only in an explicitly enabled, token-authenticated local research mode.**

---

## Context & Benchmark Evidence

In Milestone 5.1/5.2 benchmarking on the qualified holdout split, the deterministic stylometric baseline (`stylometric-baseline` v`m5.0.0`) produced:

- **AUROC:** `0.5541` (near random-chance discrimination)
- **Human False-Positive Rate (FPR):** `0.2467`

Because of this weak discrimination and high false-positive rate on human academic prose, the stylometric baseline **must never be exposed as a production AI-authorship detector**.

---

## Policy & Implementation

1. **Disabled by Default in Ordinary User-Facing and Public-Demo Modes:**
   - `RESEARCH_EXPERIMENTS_ENABLED` (`ATEVAL_ENABLE_RESEARCH_EXPERIMENTS`) defaults to `False`.
   - When `RESEARCH_EXPERIMENTS_ENABLED` is `False` (or when `PUBLIC_DEMO_MODE` is `True`), `POST /api/v1/experiments/{experiment_id}/run` refuses execution with HTTP `409 Conflict` (or `403 Forbidden` in public demo mode) and explains that no production detector is validated (`AUROC 0.5541`, `human FPR 0.2467`).
2. **Explicit Local Research Mode (`ATEVAL_ENABLE_RESEARCH_EXPERIMENTS=1`):**
   - Requires `PUBLIC_DEMO_MODE == False`.
   - Requires a valid per-launch authentication header (`X-ATEval-Token` matching `LAUNCH_TOKEN` via `hmac.compare_digest`), returning HTTP `403 Forbidden` if missing or invalid.
   - Requires the experiment to be in `'draft'` status and linked to a dataset whose `validation_json` has `schema_valid == True` and non-empty `source_distribution` (`422 Unprocessable Entity` otherwise).
   - Executes dataset evaluation off the asyncio event loop via `await run_in_threadpool(_execute_research_experiment_sync, experiment_id)`.
   - Transactionally updates the experiment status to `'completed'` and writes a `'research_experiment'` report in SQLite recording:
     - `measurement_mode: "research_measurement_only"`
     - `definitive_authorship_score: False`
     - `detector`: `{"name": "stylometric-baseline", "version": "m5.0.0", "status": "experimental_unvalidated", "benchmark_evidence": {"auroc": 0.5541, "human_fpr": 0.2467}}`
     - `dataset`: `dataset_id`, `dataset_sha256`, `evaluated_rows`, `source_distribution`
     - `configuration` and `measurements_by_label` (`count`, `mean_signal`, `median_signal`).

---

## Regression Coverage

- `tests/test_api.py::LocalApiTests::test_draft_can_be_saved_but_execution_is_truthfully_unavailable`
- `tests/test_api.py::LocalApiTests::test_bug01_experiment_execution_disabled_by_default_and_research_mode_provenance`
