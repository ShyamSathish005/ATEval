"""Frozen DistilBERT contextual-embedding intent baseline (CPU-capable).

Downloads model files only when --allow-model-download is supplied. The model
weights remain in the caller's Hugging Face cache, not this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np

from ateval.revisions.classic_models import _calibration, _labels, _macro_weighted, context_text
from ateval.revisions.datasets import load_iterater
from ateval.revisions.schema import RevisionRecord

MODEL_ID = "distilbert/distilbert-base-uncased"
MODEL_REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _embed(records, level: str, tokenizer, model, torch, *, device, batch_size: int, max_length: int) -> np.ndarray:
    texts = [context_text(record, level) for record in records]
    outputs = []
    for start in range(0, len(texts), batch_size):
        batch = tokenizer(texts[start:start + batch_size], padding=True, truncation=True, max_length=max_length, return_tensors="pt")
        batch = {key: value.to(device) for key, value in batch.items()}
        with torch.inference_mode():
            hidden = model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            # Masked mean pooling avoids treating the first-token vector as a
            # sentence-level representation by assumption.
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        outputs.append(pooled.cpu().numpy().astype(np.float32))
    return np.concatenate(outputs, axis=0) if outputs else np.zeros((0, int(model.config.dim)), dtype=np.float32)


def run(args: argparse.Namespace) -> dict:
    try:
        import torch
        import sklearn
        from huggingface_hub import snapshot_download
        from sklearn.linear_model import LogisticRegression
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Install optional dependencies: python -m pip install -e '.[revision-transformer]'") from exc

    torch.set_num_threads(args.torch_threads)
    # Keep this initial reproducible experiment on CPU. It avoids a partial
    # device-transfer path and does not depend on CUDA/MPS runtime behavior.
    device = torch.device("cpu")

    cache = Path(args.cache_dir).expanduser().resolve()
    try:
        snapshot = snapshot_download(
            repo_id=MODEL_ID, revision=MODEL_REVISION, cache_dir=str(cache),
            local_files_only=not args.allow_model_download,
            allow_patterns=["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "special_tokens_map.json"],
        )
    except Exception as exc:
        raise SystemExit(f"Pinned DistilBERT checkpoint is not cached; pass --allow-model-download to fetch it: {exc}") from exc
    snapshot_path = Path(snapshot)
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    encoder = AutoModel.from_pretrained(snapshot, local_files_only=True, use_safetensors=True).to(device)
    encoder.eval()

    def load(sentence_path: str, document_path: str, split: str):
        return load_iterater(sentence_path, split=split, source_license="Apache-2.0", license_verified=True, document_context_path=document_path).records

    train = load(args.train, args.train_documents, "train")
    dev = load(args.dev, args.dev_documents, "dev")
    test = load(args.test, args.test_documents, "test")
    if set(r.source_document_id for r in train) & (set(r.source_document_id for r in dev + test)) or set(r.source_document_id for r in dev) & set(r.source_document_id for r in test):
        raise ValueError("source-document leakage across train/dev/test")
    def is_noop(record: RevisionRecord) -> bool:
        return " ".join(record.original_text.casefold().split()) == " ".join(record.revised_text.casefold().split())
    before_counts = {name: len(rows) for name, rows in (("train", train), ("dev", dev), ("test", test))}
    noop_counts = {name: sum(map(is_noop, rows)) for name, rows in (("train", train), ("dev", dev), ("test", test))}
    train = [r for r in train if not is_noop(r)]
    dev = [r for r in dev if not is_noop(r)]
    test = [r for r in test if not is_noop(r)]
    labels = sorted(set(_labels(train) + _labels(dev) + _labels(test)))
    if "__unlabeled__" in labels:
        raise ValueError("unlabeled examples are not supported in this baseline")

    started = time.time()
    report = {
        "schema": "ateval-frozen-contextual-transformer-intent-v1",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "license": "Apache-2.0 per public Hugging Face card", "fine_tuned": False, "classifier": "balanced LogisticRegression on frozen masked-mean contextual embeddings"},
        "device": str(device), "seed": args.seed, "max_length": args.max_length, "batch_size": args.batch_size,
        "source_document_leakage": False,
        "records_before_noop_filter": before_counts,
        "exact_text_noop_records_excluded": noop_counts,
        "records_after_noop_filter": {"train": len(train), "dev": len(dev), "test": len(test)},
        "contexts": {},
    }
    fitted = {}
    for context_level in ("sentence", "local"):
        x_train = _embed(train, context_level, tokenizer, encoder, torch, device=device, batch_size=args.batch_size, max_length=args.max_length)
        x_dev = _embed(dev, context_level, tokenizer, encoder, torch, device=device, batch_size=args.batch_size, max_length=args.max_length)
        x_test = _embed(test, context_level, tokenizer, encoder, torch, device=device, batch_size=args.batch_size, max_length=args.max_length)
        train_labels, dev_labels, test_labels = _labels(train), _labels(dev), _labels(test)
        trials = []
        for c_value in (0.1, 1.0, 10.0):
            classifier = LogisticRegression(C=c_value, class_weight="balanced", max_iter=1000, random_state=args.seed)
            classifier.fit(x_train, train_labels)
            score = _macro_weighted(dev_labels, list(classifier.predict(x_dev)), labels)["macro_f1"]
            trials.append((score or 0.0, c_value))
        _, selected_c = max(trials, key=lambda item: (item[0], -item[1]))
        classifier = LogisticRegression(C=selected_c, class_weight="balanced", max_iter=1000, random_state=args.seed)
        classifier.fit(x_train, train_labels)
        predicted = list(map(str, classifier.predict(x_test)))
        probabilities = classifier.predict_proba(x_test)
        class_order = list(map(str, classifier.classes_))
        probs = [[float(probabilities[row, class_order.index(label)]) if label in class_order else 0.0 for label in labels] for row in range(len(test))]
        metrics = _macro_weighted(test_labels, predicted, labels)
        metrics["calibration"] = _calibration(test_labels, labels, probs)
        metrics["calibration"]["interpretation"] = "uncalibrated logistic-head scores; ECE/Brier are held-out diagnostics"
        metrics["selected_C_by_dev_macro_f1"] = selected_c
        metrics["per_class"] = metrics["per_class"]
        domain_results = {}
        domains = [str(r.metadata.get("domain") or "unknown") for r in test]
        for domain in sorted(set(domains)):
            indexes = [i for i, value in enumerate(domains) if value == domain]
            domain_results[domain] = {"n": len(indexes), **_macro_weighted([test_labels[i] for i in indexes], [predicted[i] for i in indexes], labels)}
        metrics["test_by_domain"] = domain_results
        report["contexts"][context_level] = metrics
        fitted[context_level] = classifier
    report["training_seconds"] = round(time.time() - started, 3)
    report["label_order"] = labels
    report["human_evaluation"] = "not conducted"
    report["semantic_equivalence"] = "not assessed"
    report["warning"] = "Frozen general-domain English encoder and small imbalanced revision corpus; intent classification is not edit necessity or semantic validation."

    output = Path(args.output_dir)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite transformer experiment: {output}")
    output.mkdir(parents=True)
    import joblib
    from ateval import __version__
    from ateval.revisions import classic_models, datasets, schema, taxonomy
    source_files = [Path(__file__), Path(classic_models.__file__), Path(datasets.__file__), Path(schema.__file__), Path(taxonomy.__file__)]
    source_hash = hashlib.sha256("".join(_digest(path) for path in source_files).encode()).hexdigest()
    manifest_hashes = {str(path): _digest(path) for path in Path("data/manifests").glob("revision_*_manifest.json")}
    encoder_files = {path.name: _digest(path) for path in snapshot_path.iterdir() if path.is_file() and path.name in {"config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "special_tokens_map.json"}}
    for context_level, classifier in fitted.items():
        weights = output / f"{context_level}-logistic-head.joblib"
        joblib.dump(classifier, weights)
        report.setdefault("artifacts", {})[weights.name] = _digest(weights)
        (output / f"{context_level}-metadata.json").write_text(json.dumps({
            "schema": "ateval-contextual-transformer-metadata-v1", "context_level": context_level,
            "dataset_manifests_sha256": manifest_hashes, "source_code_sha256": source_hash,
            "training_configuration": {"seed": args.seed, "selected_C": report["contexts"][context_level]["selected_C_by_dev_macro_f1"], "max_length": args.max_length, "batch_size": args.batch_size, "pooling": "attention-mask-weighted mean of final hidden states", "encoder_frozen": True},
            "encoder": {"model_id": MODEL_ID, "revision": MODEL_REVISION, "license": "Apache-2.0", "files_sha256": encoder_files, "weights_saved_in_project": False},
            "environment": {"python": platform.python_version(), "torch": torch.__version__, "transformers": __import__("transformers").__version__, "scikit_learn": sklearn.__version__, "platform": platform.platform(), "device": str(device), "ateval": __version__},
            "weight_file": weights.name, "sha256": _digest(weights), "evaluation_report": "comparison.json",
        }, indent=2) + "\n", encoding="utf-8")
    (output / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train")
    parser.add_argument("dev")
    parser.add_argument("test")
    parser.add_argument("--train-documents", required=True)
    parser.add_argument("--dev-documents", required=True)
    parser.add_argument("--test-documents", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir", default="~/.cache/huggingface/hub")
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--torch-threads", type=int, default=4)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({"output_dir": args.output_dir, "device": report["device"], "training_seconds": report["training_seconds"], "contexts": {name: {"macro_f1": result["macro_f1"], "accuracy": result["accuracy"]} for name, result in report["contexts"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
