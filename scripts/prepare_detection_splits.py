"""Prepare reproducible, leakage-resistant train/val/test splits for detection benchmarking.

Saves manifests under data/manifests/ and records data provenance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ateval.detection import (  # noqa: E402
    DatasetManifest,
    DetectionRecord,
    SplitConfig,
    SyntheticDetectionFixture,
    TXD22Adapter,
    compute_sha256,
    create_leakage_resistant_splits,
    create_length_matched_cohort,
    prepare_task_a_cohort,
    prepare_task_b_cohort,
)

DEFAULT_INPUT = Path("data/raw/txd_22/txd22_raw.csv")
MANIFEST_DIR = Path("data/manifests")


def prepare_splits(
    input_path: Path = DEFAULT_INPUT,
    *,
    manifest_dir: Path = MANIFEST_DIR,
    max_records: int | None = None,
    unseen_models: tuple[str, ...] = (),
    seed: int = 42,
) -> dict[str, Any]:
    manifest_dir.mkdir(parents=True, exist_ok=True)

    if input_path.exists():
        print(f"Loading external corpus from {input_path}...")
        load_res = TXD22Adapter.load(input_path, verify_sha256=False, max_records=max_records)
        records = load_res.records
        file_hash = load_res.sha256_hash
        file_size = input_path.stat().st_size
        print(f"Loaded {len(records):,} valid records from {load_res.total_rows_read:,} rows.")
    else:
        print(f"Warning: {input_path} not found. Using synthetic fixture for offline execution.")
        records = SyntheticDetectionFixture.create_fixture_records()
        file_hash = "synthetic_offline_fixture_sha256"
        file_size = 0

    # 1. Dataset provenance manifest
    dataset_manifest = DatasetManifest(
        name="TXD-22",
        version="1.0",
        source="Mendeley Data",
        doi="10.17632/prcjcggtjf.1",
        licence="CC BY 4.0",
        citation="Iqbal, Md Sadiq; Kashem, Mohammod Abul (2026), 'TXD-22: A Large-Scale Benchmark Dataset for Multi-Class AI-Generated and Mixed-Source Text Identification', Mendeley Data, v1, http://doi.org/10.17632/prcjcggtjf.1",
        download_url="https://data.mendeley.com/public-files/datasets/prcjcggtjf/files/1e842f9d-4ff8-4986-bc7c-cde460f806ee/file_downloaded",
        download_date="2026-11-03",
        sha256_hash=file_hash,
        file_size_bytes=file_size,
        total_samples=len(records),
        class_distribution=dict(load_res.class_distribution) if input_path.exists() else {"Human": 5, "AI": 5, "Mixed": 2},
        transformations=[
            "Decode UTF-8-SIG; deterministic Latin-1 fallback for TXD-22 v1 legacy bytes",
            "Preserve verbatim Source as original_label",
            "Map Source to Task A (human/ai) and Task B (mixed)",
            "Extract prompt / Question as grouping key to prevent prompt leakage",
            f"Hold out unseen generator models in test: {list(unseen_models)}",
        ],
        qualification_status="approved",
        qualification_notes="Approved for experimental benchmarking under CC BY 4.0.",
    )
    dataset_manifest_path = manifest_dir / "txd22_dataset_manifest.json"
    dataset_manifest.save(dataset_manifest_path)
    print(f"Saved dataset manifest to {dataset_manifest_path}")

    # 2. Extract Task A cohort (pure human vs pure AI)
    task_a_records = prepare_task_a_cohort(records)
    print(f"Task A cohort size (pure human vs pure AI): {len(task_a_records):,}")

    # 3. Create leakage-resistant splits
    split_cfg = SplitConfig(
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=seed,
        group_by="prompt",
        unseen_models=unseen_models,
    )
    split_res = create_leakage_resistant_splits(task_a_records, split_cfg)
    print("Leakage audit:", json.dumps(split_res.leakage_audit, indent=2))
    if not split_res.leakage_audit["clean"]:
        raise ValueError("Leakage detected across benchmark splits; refusing to write manifests.")
    for split_name, split_records in (
        ("train", split_res.train),
        ("validation", split_res.val),
        ("test", split_res.test),
    ):
        classes = {record.label for record in split_records}
        if classes != {"human", "ai"}:
            raise ValueError(
                f"{split_name} split has classes {sorted(classes)!r}; "
                "refusing a degenerate binary benchmark. "
                "TXD-22 prompt grouping can make unseen-model holdouts incompatible "
                "with class-balanced train/validation splits."
            )

    # 4. Save train, val, test manifests
    def _save_manifest(recs: list[DetectionRecord], target: Path, meta: dict[str, Any]) -> None:
        payload = {
            "metadata": meta,
            "count": len(recs),
            "records": [r.to_dict() for r in recs],
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {len(recs):,} records to {target}")

    _save_manifest(split_res.train, manifest_dir / "txd22_train_manifest.json", {
        "split": "train", "group_by": split_cfg.group_by, "seed": seed,
    })
    _save_manifest(split_res.val, manifest_dir / "txd22_val_manifest.json", {
        "split": "validation", "group_by": split_cfg.group_by, "seed": seed,
    })
    _save_manifest(split_res.test, manifest_dir / "txd22_test_manifest.json", {
        "split": "test", "group_by": split_cfg.group_by, "seed": seed,
        "unseen_models": list(unseen_models),
    })

    # 5. Length-matched test cohort
    length_matched = create_length_matched_cohort(split_res.test, bin_width=40, seed=seed)
    _save_manifest(length_matched, manifest_dir / "txd22_length_matched_test.json", {
        "split": "test_length_matched", "bin_width": 40, "seed": seed,
    })

    # 6. Task B mixed authorship manifest
    task_b_records = prepare_task_b_cohort(records, include_controls=True)
    _save_manifest(task_b_records, manifest_dir / "txd22_mixed_authorship_manifest.json", {
        "task": "task_b_mixed_authorship", "seed": seed,
    })

    summary = {
        "dataset_manifest": str(dataset_manifest_path),
        "total_records": len(records),
        "task_a_total": len(task_a_records),
        "train_count": len(split_res.train),
        "val_count": len(split_res.val),
        "test_count": len(split_res.test),
        "unseen_model_test_count": len(split_res.unseen_model_test),
        "length_matched_test_count": len(length_matched),
        "task_b_mixed_count": len(task_b_records),
        "leakage_clean": split_res.leakage_audit["clean"],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to raw TXD-22 CSV")
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR, help="Manifest output directory")
    parser.add_argument("--max-records", type=int, default=None, help="Max records to load")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    parser.add_argument(
        "--unseen-model",
        action="append",
        default=[],
        help="Hold out a generator model only when prompt/document grouping remains valid; repeatable",
    )
    args = parser.parse_args()

    summary = prepare_splits(
        args.input,
        manifest_dir=args.manifest_dir,
        max_records=args.max_records,
        unseen_models=tuple(args.unseen_model),
        seed=args.seed,
    )
    print("Split preparation summary:", json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
