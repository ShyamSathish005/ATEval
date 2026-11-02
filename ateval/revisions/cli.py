"""Reproducible local dataset and intention-baseline commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classification import MultinomialIntentModel
from .datasets import load_arxivedits, load_iterater
from .evaluation import classification_metrics, fitted_majority_metrics
from .classic_models import train_compare
from .generation_baselines import compare_generation_baselines, compare_generation_systems
from .academic_generation import (
    AcademicRevisionRequest, GeneralInstructionGenerator, IteraTeRSeq2SeqGenerator,
    XtraGPTLocalGenerator, XtraGPTOllamaGenerator, checkpoint_manifest, proposal_for_record, runtime_metadata,
)
from .scar import SCARRevisionEngine


def add_revisions_parser(subparsers: Any) -> None:
    revisions = subparsers.add_parser("revisions", help="Inspect revision corpora and run CPU intent baselines")
    actions = revisions.add_subparsers(dest="revisions_command", required=True)
    for action in ("inspect", "train-intent", "evaluate-intent", "benchmark-intent", "benchmark-generation", "benchmark-generation-model", "propose", "scar-revise", "predict-trained-intent"):
        command = actions.add_parser(action)
        if action == "scar-revise":
            command.add_argument("sentence", help="Selected sentence to plan and optionally revise")
            command.add_argument("--paragraph-context", required=True)
            command.add_argument("--section", default="unknown")
            command.add_argument("--intention", choices=("no_edit", "clarity", "grammar", "redundancy", "structure", "technical_review"), default="no_edit")
            command.add_argument("--author-requested-edit", action="store_true")
            command.add_argument("--protected-term", action="append", default=[])
            command.add_argument("--citation", action="append", default=[])
            command.add_argument("--ollama-model", default="ateval-xtragpt-1_5b-q8_0")
            command.add_argument(
                "--model-file",
                default=str(Path.home() / ".cache" / "ateval" / "models" / "XtraGPT-1.5B-q4.gguf"),
            )
            command.add_argument("--ollama-url", default="http://127.0.0.1:11434")
            continue
        if action == "propose":
            command.add_argument("sentence", help="Original target sentence or passage")
            command.add_argument("--paragraph-context", default="")
            command.add_argument("--previous-sentence", default="")
            command.add_argument("--next-sentence", default="")
            command.add_argument("--section", default="unknown")
            command.add_argument("--instruction", default="Improve academic clarity conservatively.")
            command.add_argument("--iterater-intent", choices=("clarity", "fluency", "coherence", "style", "meaning-changed", "others"), default="clarity")
            command.add_argument("--protected-term", action="append", default=[])
            command.add_argument("--citation", action="append", default=[])
            command.add_argument("--model-path", required=True, help="Existing local checkpoint directory; no downloads occur")
            command.add_argument("--ollama-model", default="ateval-xtragpt-1_5b-q4", help="Local GGUF model tag for xtragpt-ollama")
            command.add_argument("--backend", choices=("xtragpt", "xtragpt-ollama", "general", "iterater-bart", "iterater-pegasus"), default="xtragpt")
            command.add_argument("--context-length", type=int, default=2048, help="Ollama context window for xtragpt-ollama")
            command.add_argument("--ollama-url", default="http://127.0.0.1:11434")
            command.add_argument("--max-new-tokens", type=int, default=512)
            command.add_argument("--max-input-tokens", type=int, default=8192)
            command.add_argument("--dtype", choices=("float16", "bfloat16", "float32"), default="float16")
            continue
        if action == "predict-trained-intent":
            command.add_argument("sentence", help="A sentence the author wants an advisory annotation for")
            command.add_argument("--context-before", default="", help="Optional neighboring paragraph text")
            command.add_argument("--context-after", default="", help="Optional neighboring paragraph text")
            command.add_argument("--section-type", default="unknown")
            continue
        if action == "benchmark-generation":
            command.add_argument("test_file", help="Local held-out human sentence-pair export")
            command.add_argument("--test-documents", help="Matching document-level export for context metadata")
            command.add_argument("--source-license", default="Apache-2.0")
            command.add_argument("--license-verified", action="store_true")
            command.add_argument("--output", required=True, help="New JSON comparison report")
            continue
        if action == "benchmark-generation-model":
            command.add_argument("test_file", help="Prepared document-grouped held-out sentence-pair export")
            command.add_argument("--test-documents", help="Matching document-level export for context metadata")
            command.add_argument("--test-manifest", required=True, help="Immutable grouped-test manifest; verifies exact files and split isolation")
            command.add_argument("--source-license", default="Apache-2.0")
            command.add_argument("--license-verified", action="store_true", help="Confirm the evaluation corpus is licensed for this research use")
            command.add_argument("--model-path", required=True, help="Existing local checkpoint directory; no downloads occur")
            command.add_argument("--model-id", required=True, help="Checkpoint ID/revision used for this local directory")
            command.add_argument("--ollama-model", default="ateval-xtragpt-1_5b-q4", help="Local GGUF model tag for xtragpt-ollama")
            command.add_argument("--model-license", required=True, help="Verified checkpoint license identifier")
            command.add_argument("--model-license-reviewed", action="store_true", help="Confirm checkpoint and base-model terms were reviewed")
            command.add_argument("--training-data-license-note", default="not independently verified; model license does not grant training-text rights", help="Separate record for the checkpoint's training data rights")
            command.add_argument("--backend", choices=("xtragpt", "xtragpt-ollama", "general", "iterater-bart", "iterater-pegasus"), default="xtragpt")
            command.add_argument("--context-length", type=int, default=2048, help="Ollama context window for xtragpt-ollama")
            command.add_argument("--ollama-url", default="http://127.0.0.1:11434")
            command.add_argument("--predictions-output", help="Optional new JSONL containing per-example source, reference, output and preservation results")
            command.add_argument("--prompt-mode", choices=("published", "ateval"), default="ateval")
            command.add_argument("--output", required=True, help="New comparison JSON; refuses overwrites")
            command.add_argument("--max-new-tokens", type=int, default=512)
            command.add_argument("--max-input-tokens", type=int, default=8192)
            command.add_argument("--dtype", choices=("float16", "bfloat16", "float32"), default="float16")
            continue
        if action == "benchmark-intent":
            command.add_argument("train_file", help="HUMAN training JSON/JSONL/CSV export")
            command.add_argument("dev_file", help="HUMAN validation export")
            command.add_argument("test_file", help="HUMAN held-out test export")
            command.add_argument("--train-documents", help="Paired training document export for local/document context")
            command.add_argument("--dev-documents", help="Paired validation document export")
            command.add_argument("--test-documents", help="Paired test document export")
            command.add_argument("--source-license", default="Apache-2.0", help="Verified source license identifier")
            command.add_argument("--license-verified", action="store_true", help="Acknowledge dataset and source terms were reviewed")
            command.add_argument("--seed", type=int, default=17)
            command.add_argument("--output-dir", required=True, help="New experiment directory; must not already exist")
            continue
        if action == "evaluate-intent":
            command.add_argument("model", help="Previously trained JSON model")
        command.add_argument("dataset", choices=("iterater", "arxivedits"))
        command.add_argument("file", help="User-provided local JSON/JSONL/CSV export")
        command.add_argument("--split", help="Declared source split; use train/dev/test from corpus")
        command.add_argument("--level", choices=("sentence", "document"), default="sentence")
        command.add_argument("--variant", choices=("human", "full"), default="human")
        command.add_argument("--license", dest="source_license", help="Source license documented by the user after review")
        command.add_argument("--license-verified", action="store_true", help="Acknowledge provenance review for this local export")
        command.add_argument("--manifest", help="arXivEdits per-paper/version JSON license manifest")
        command.add_argument("--permitted-license", action="append", default=[], help="Exact license id permitted for this use (repeatable)")
        if action == "train-intent":
            command.add_argument("--output", required=True, help="New JSON model path; existing files are never overwritten")


def _load(args: argparse.Namespace):
    if args.dataset == "iterater":
        return load_iterater(args.file, split=args.split, level=args.level, variant=args.variant, source_license=args.source_license, license_verified=args.license_verified)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8")) if args.manifest else None
    return load_arxivedits(args.file, split=args.split, license_manifest=manifest, permitted_licenses=set(args.permitted_license))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_grouped_test_manifest(test_file: str, test_documents: str | None, manifest_file: str) -> dict[str, Any]:
    """Verify exact grouped-test inputs and disjoint train/dev document groups."""
    manifest_path = Path(manifest_file).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    project_root = manifest_path.parent.parent.parent
    def resolve_recorded(value: str) -> Path:
        recorded_path = Path(value)
        return (project_root / recorded_path).resolve() if not recorded_path.is_absolute() else recorded_path.resolve()
    expected_test = resolve_recorded(manifest["processed_sentence_file"])
    expected_docs = resolve_recorded(manifest["processed_document_file"])
    actual_test = Path(test_file).expanduser().resolve()
    actual_docs = Path(test_documents).expanduser().resolve() if test_documents else None
    if actual_test != expected_test or actual_docs != expected_docs:
        raise ValueError("test files must exactly match the paths in --test-manifest")
    for path, digest_key in ((actual_test, "processed_sentence_sha256"), (actual_docs, "processed_document_sha256")):
        if path is None:
            raise ValueError("--test-documents is required when validating the grouped-test manifest")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest[digest_key]:
            raise ValueError(f"{path} checksum does not match --test-manifest")
    test_rows = _read_jsonl(actual_test)
    if len(test_rows) != manifest["row_count"]:
        raise ValueError("held-out row count does not match --test-manifest")
    record_ids = [str(row.get("record_id", "")) for row in test_rows]
    if record_ids != manifest["record_ids"]:
        raise ValueError("held-out record order/IDs do not match --test-manifest")
    test_docs = {str(row.get("doc_id", "")) for row in test_rows}
    digest = hashlib.sha256("\n".join(sorted(test_docs)).encode()).hexdigest()
    if len(test_docs) != manifest["document_count"] or digest != manifest["source_document_ids_sha256"]:
        raise ValueError("held-out document groups do not match --test-manifest")
    split_documents = {manifest["split"]: test_docs}
    for split, sibling in (("train", "revision_training_manifest.json"), ("dev", "revision_validation_manifest.json")):
        sibling_path = manifest_path.with_name(sibling)
        if not sibling_path.is_file():
            raise ValueError(f"Required sibling manifest missing for {split}: {sibling_path}")
        sibling_manifest = json.loads(sibling_path.read_text(encoding="utf-8"))
        sentence_path = resolve_recorded(sibling_manifest["processed_sentence_file"])
        sentence_rows = _read_jsonl(sentence_path)
        ids = {str(row.get("doc_id", "")) for row in sentence_rows}
        computed = hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()
        if computed != sibling_manifest["source_document_ids_sha256"]:
            raise ValueError(f"{split} document groups do not match their immutable manifest")
        split_documents[split] = ids
    if (
        split_documents["test"] & split_documents["train"]
        or split_documents["test"] & split_documents["dev"]
        or split_documents["train"] & split_documents["dev"]
    ):
        raise ValueError("document leakage detected between held-out, training, and validation manifests")
    return {"manifest": str(manifest_path), "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "document_leakage": False}


def run_revisions(args: argparse.Namespace) -> int:
    if args.revisions_command == "scar-revise":
        paragraph = args.paragraph_context
        start = paragraph.find(args.sentence)
        if start < 0:
            raise ValueError("sentence must occur in --paragraph-context")
        from .scar import revision_necessity_gate
        gate = revision_necessity_gate(
            selected_text=args.sentence,
            paragraph_context=paragraph,
            intention=args.intention,
            author_requested_edit=args.author_requested_edit,
        )
        generator = None
        if gate.decision in {"CLARITY_IMPROVEMENT", "GRAMMAR_IMPROVEMENT", "REDUNDANCY_REVIEW", "STRUCTURAL_IMPROVEMENT"}:
            generator = XtraGPTOllamaGenerator(
                args.ollama_model, model_file=args.model_file, base_url=args.ollama_url,
                mode="published", max_new_tokens=192, context_length=2048,
            )
        result = SCARRevisionEngine(generator).revise(
            paragraph,
            target_start=start,
            target_end=start + len(args.sentence),
            intention=args.intention,
            author_requested_edit=args.author_requested_edit,
            protected_terms=tuple(args.protected_term),
            citations=tuple(args.citation),
            section=args.section,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.revisions_command == "propose":
        request = AcademicRevisionRequest(
            original_text=args.sentence,
            paragraph_context=args.paragraph_context,
            previous_sentence=args.previous_sentence,
            next_sentence=args.next_sentence,
            document_section=args.section,
            editing_instruction=args.instruction,
            iterater_intent=args.iterater_intent,
            protected_terminology=tuple(args.protected_term),
            relevant_citations=tuple(args.citation),
        )
        if args.backend == "xtragpt-ollama":
            generator = XtraGPTOllamaGenerator(
                args.ollama_model,
                model_file=args.model_path, base_url=args.ollama_url, mode=args.prompt_mode if args.revisions_command == "benchmark-generation-model" else "published",
                max_new_tokens=args.max_new_tokens, context_length=args.context_length,
            )
        elif args.backend == "iterater-bart":
            generator = IteraTeRSeq2SeqGenerator(args.model_path, model_name="iterater_bart")
        elif args.backend == "iterater-pegasus":
            generator = IteraTeRSeq2SeqGenerator(args.model_path, model_name="iterater_pegasus")
        elif args.backend == "general":
            generator = GeneralInstructionGenerator(
                args.model_path, mode="ateval", max_new_tokens=args.max_new_tokens,
                max_input_tokens=args.max_input_tokens, dtype=args.dtype,
            )
        else:
            generator = XtraGPTLocalGenerator(
                args.model_path, mode="ateval", max_new_tokens=args.max_new_tokens,
                max_input_tokens=args.max_input_tokens, dtype=args.dtype,
            )
        proposal = generator.generate(request)
        output = proposal.to_dict()
        if getattr(generator, "telemetry", None):
            output["inference"] = generator.telemetry[-1]
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    if args.revisions_command == "predict-trained-intent":
        import platform
        from types import SimpleNamespace
        import joblib
        from .classic_models import context_text
        model_dir = Path(__file__).resolve().parents[2] / "models" / "revisions" / "iterater_human_grouped_v1"
        model_path = model_dir / "local-logistic_regression.joblib"
        metadata_path = model_dir / "local-logistic_regression.metadata.json"
        if not model_path.is_file() or not metadata_path.is_file():
            raise ValueError("The trained IteraTeR-HUMAN model is unavailable; run benchmark-intent first")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != metadata.get("sha256"):
            raise ValueError("Intent model checksum does not match its metadata")
        model = joblib.load(model_path)
        record = SimpleNamespace(section_type=args.section_type, context_before=args.context_before, context_after=args.context_after, original_text=args.sentence, metadata={})
        scores = model.predict_proba([context_text(record, "local")])[0]
        classes = list(map(str, model.classes_))
        best = max(range(len(scores)), key=lambda index: float(scores[index]))
        comparison = json.loads((model_dir / "comparison.json").read_text(encoding="utf-8"))
        print(json.dumps({
            "predicted_intent": classes[best], "top_class_score": float(scores[best]),
            "score_kind": "uncalibrated LogisticRegression predict_proba output; not a probability of correctness",
            "decision": "advisory_only", "modification_necessary": None,
            "automatic_edit_applied": False, "author_review_required": True,
            "held_out_macro_f1": comparison["models"]["local"]["logistic_regression"]["macro_f1"],
            "python_runtime": platform.python_version(),
        }, indent=2))
        return 0
    if args.revisions_command == "benchmark-intent":
        if not args.license_verified:
            raise ValueError("Benchmarking requires --license-verified after reviewing the dataset and source terms")
        train = load_iterater(args.train_file, split="train", source_license=args.source_license, license_verified=True, document_context_path=args.train_documents).records
        dev = load_iterater(args.dev_file, split="dev", source_license=args.source_license, license_verified=True, document_context_path=args.dev_documents).records
        test = load_iterater(args.test_file, split="test", source_license=args.source_license, license_verified=True, document_context_path=args.test_documents).records
        report = train_compare(train, dev, test, output_dir=args.output_dir, seed=args.seed)
        print(json.dumps({"output_dir": str(Path(args.output_dir)), "comparison": report}, indent=2, ensure_ascii=False))
        return 0
    if args.revisions_command == "benchmark-generation":
        if not args.license_verified:
            raise ValueError("Generation benchmarking requires --license-verified after reviewing data/source terms")
        test = load_iterater(args.test_file, split="test", source_license=args.source_license, license_verified=True, document_context_path=args.test_documents).records
        if not test:
            raise ValueError("No test records loaded from local export")
        report = compare_generation_baselines(test, output_path=args.output)
        print(json.dumps({"output": str(Path(args.output)), "systems": report["systems"]}, indent=2, ensure_ascii=False))
        return 0
    if args.revisions_command == "benchmark-generation-model":
        if not args.license_verified:
            raise ValueError("Benchmarking requires --license-verified after reviewing the evaluation corpus terms")
        if not args.model_license_reviewed:
            raise ValueError("Review the checkpoint and its upstream base-model terms, then pass --model-license-reviewed")
        test_provenance = _validate_grouped_test_manifest(args.test_file, args.test_documents, args.test_manifest)
        records = load_iterater(
            args.test_file, split="test", source_license=args.source_license,
            license_verified=True, document_context_path=args.test_documents,
        ).records
        if not records:
            raise ValueError("No held-out records were loaded")
        if args.backend == "xtragpt-ollama":
            generator = XtraGPTOllamaGenerator(
                args.ollama_model, model_file=args.model_path, base_url=args.ollama_url,
                mode=args.prompt_mode, max_new_tokens=args.max_new_tokens,
                context_length=args.context_length,
            )
        elif args.backend == "iterater-bart":
            generator = IteraTeRSeq2SeqGenerator(args.model_path, model_name="iterater_bart")
        elif args.backend == "iterater-pegasus":
            generator = IteraTeRSeq2SeqGenerator(args.model_path, model_name="iterater_pegasus")
        elif args.backend == "general":
            generator = GeneralInstructionGenerator(
                args.model_path, mode="ateval", max_new_tokens=args.max_new_tokens,
                max_input_tokens=args.max_input_tokens, dtype=args.dtype,
            )
        else:
            generator = XtraGPTLocalGenerator(
                args.model_path, mode=args.prompt_mode, max_new_tokens=args.max_new_tokens,
                max_input_tokens=args.max_input_tokens, dtype=args.dtype,
            )
        if args.predictions_output and Path(args.predictions_output).exists():
            raise FileExistsError(f"Refusing to overwrite predictions file: {args.predictions_output}")
        run_started_at = datetime.now(timezone.utc).isoformat()
        generation_start = time.perf_counter()
        proposals = []
        for index, record in enumerate(records, start=1):
            proposals.append(proposal_for_record(record, generator))
            if index % 10 == 0 or index == len(records):
                print(f"XtraGPT inference: {index}/{len(records)}", file=sys.stderr, flush=True)
        generation_seconds = time.perf_counter() - generation_start
        system_name = args.backend if args.backend.startswith("iterater-") else f"{args.backend}_{args.prompt_mode}"
        generated = {system_name: [proposal.proposed_text for proposal in proposals]}
        seq2seq = args.backend.startswith("iterater-")
        report = compare_generation_systems(
            records, generated,
            model_metadata={
                "model_id": args.model_id,
                "test_manifest": test_provenance,
                "local_path": str(Path(args.model_path).expanduser().resolve()),
                "local_checkpoint_manifest": generator.checkpoint_manifest() if hasattr(generator, "checkpoint_manifest") else checkpoint_manifest(args.model_path),
                "checkpoint_license": args.model_license,
                "training_data_license_note": args.training_data_license_note,
                "backend": args.backend,
                "run_started_at": run_started_at,
                "generation_wall_seconds": generation_seconds,
                "actual_quantization_reported_by_runtime": "Q8_0 (upstream filename contains q4; filename was not treated as evidence of tensor quantization)",
                "upstream_repository_revision": "ebbce0efe4c726fd26df88237117367216ca42c6",
                "upstream_artifact_size_bytes": 1646573088,
                "prompt_mode": args.prompt_mode if args.backend in {"xtragpt", "xtragpt-ollama", "general"} else "official_iterater_intent_prefix",
                "intent_conditioning": "held-out record's gold IteraTeR intention label, mapped into an editing instruction",
                "decoding": (
                    {"num_beams": 8, "max_length": 1024}
                    if seq2seq
                    else ({"temperature": 0.1, "seed": 17, "max_new_tokens": args.max_new_tokens,
                           "num_ctx": args.context_length}
                          if args.backend == "xtragpt-ollama"
                          else {"do_sample": False, "num_beams": 1, "max_new_tokens": args.max_new_tokens, "dtype": args.dtype})
                ),
                "context": (
                    "original sentence only, following official IteraTeR sentence-model protocol"
                    if args.backend.startswith("iterater-")
                    else "selected sentence plus available adjacent source sentence context and section label (proxy context, not full paper context)"
                ),
                "runtime": generator.runtime_metadata() if hasattr(generator, "runtime_metadata") else runtime_metadata(),
                "inference_telemetry": getattr(generator, "telemetry", None),
                "adapter_source_sha256": hashlib.sha256(Path(__file__).with_name("academic_generation.py").read_bytes()).hexdigest(),
                "author_review_required": True,
            },
            output_path=args.output,
        )
        if args.predictions_output:
            predictions_path = Path(args.predictions_output)
            predictions_path.parent.mkdir(parents=True, exist_ok=True)
            with predictions_path.open("w", encoding="utf-8") as stream:
                for index, (record, proposal) in enumerate(zip(records, proposals)):
                    row = {
                        "record_id": record.record_id,
                        "source_document_id": record.source_document_id,
                        "section_type": record.section_type,
                        "source": record.original_text,
                        "reference": record.revised_text,
                        "output": proposal.proposed_text,
                        "warnings": list(proposal.warnings),
                        "preservation": proposal.preservation,
                        "status": proposal.status,
                        "author_review_required": proposal.author_review_required,
                        "inference": generator.telemetry[index] if index < len(getattr(generator, "telemetry", [])) else None,
                    }
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({"output": str(Path(args.output)), "systems": report["systems"]}, ensure_ascii=False, indent=2))
        return 0
    result = _load(args)
    label_counts = Counter(label for record in result.records for label in record.canonical_labels)
    common = {"dataset": args.dataset, "variant": getattr(args, "variant", "human"), "split": args.split, "records": len(result.records), "skipped": dict(result.skipped), "labels": dict(sorted(label_counts.items())), "warnings": result.warnings}
    if args.revisions_command == "inspect":
        print(json.dumps({**common, "source_documents": len({record.source_document_id for record in result.records}), "verified_records": sum(record.license_verified for record in result.records)}, indent=2, ensure_ascii=False))
        return 0
    if not result.records:
        raise ValueError("No eligible revision records were loaded; inspect provenance, format, split, and license settings")
    if args.revisions_command == "train-intent":
        if not args.split or args.split.casefold() not in {"train", "training"}:
            raise ValueError("Intent-model training requires the corpus training split")
        model = MultinomialIntentModel().fit(result.records)
        model.save(args.output)
        print(json.dumps({**common, "model": str(Path(args.output)), "classes": dict(model.class_counts), "training_source_documents": len(model.training_source_ids), "baseline": "multinomial-naive-bayes-cpu"}, indent=2, ensure_ascii=False))
        return 0
    if not args.split or args.split.casefold() not in {"test", "testing", "eval", "evaluation"}:
        raise ValueError("Intent-model evaluation requires a held-out test/evaluation split")
    model = MultinomialIntentModel.load(args.model)
    metrics = classification_metrics(result.records, model)
    majority = fitted_majority_metrics(result.records, model)
    print(json.dumps({**common, "metrics": metrics, "majority_baseline": majority, "baseline": "multinomial-naive-bayes-cpu"}, indent=2, ensure_ascii=False))
    return 0
