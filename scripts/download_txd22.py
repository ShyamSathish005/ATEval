"""Reproducible download and verification script for TXD-22 dataset.

Source: Mendeley Data (DOI: 10.17632/prcjcggtjf.1)
Licence: CC BY 4.0
Expected SHA-256: 232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d
Expected Size: 121,656,267 bytes
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import urllib.request
from pathlib import Path

MENDELEY_DOWNLOAD_URL = (
    "https://data.mendeley.com/public-files/datasets/prcjcggtjf/files/"
    "1e842f9d-4ff8-4986-bc7c-cde460f806ee/file_downloaded"
)
EXPECTED_SHA256 = "232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d"
EXPECTED_SIZE = 121656267
DEFAULT_TARGET = Path("data/raw/txd_22/txd22_raw.csv")


def download_txd22(
    target_path: Path = DEFAULT_TARGET,
    *,
    verify: bool = True,
    sample_bytes: int | None = None,
) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_path.with_suffix(".tmp")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ATEval/0.1.0",
    }
    if sample_bytes:
        headers["Range"] = f"bytes=0-{sample_bytes - 1}"

    req = urllib.request.Request(MENDELEY_DOWNLOAD_URL, headers=headers)
    print(f"Connecting to Mendeley Data: {MENDELEY_DOWNLOAD_URL}")
    t0 = time.time()
    hasher = hashlib.sha256()
    bytes_downloaded = 0

    with urllib.request.urlopen(req, timeout=30) as response, open(temp_target, "wb") as out_stream:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            out_stream.write(chunk)
            hasher.update(chunk)
            bytes_downloaded += len(chunk)
            if sample_bytes and bytes_downloaded >= sample_bytes:
                break
            if bytes_downloaded % (1024 * 1024 * 5) < 65536:
                elapsed = time.time() - t0
                speed = (bytes_downloaded / 1024 / 1024) / elapsed if elapsed else 0
                print(f"Downloaded {bytes_downloaded / 1024 / 1024:.1f} MB ({speed:.2f} MB/s)...")

    digest = hasher.hexdigest()
    elapsed = time.time() - t0
    print(f"Downloaded {bytes_downloaded:,} bytes in {elapsed:.1f}s.")
    print(f"SHA-256: {digest}")

    if not sample_bytes and verify:
        if digest != EXPECTED_SHA256:
            temp_target.unlink(missing_ok=True)
            raise ValueError(
                f"SHA-256 verification failed!\nExpected: {EXPECTED_SHA256}\nCalculated: {digest}"
            )
        print("SHA-256 verification: PASSED (exact match)")

    temp_target.replace(target_path)
    print(f"Saved dataset to {target_path}")
    return target_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_TARGET, help="Output target path")
    parser.add_argument("--no-verify", action="store_true", help="Skip SHA-256 verification")
    parser.add_argument("--sample-bytes", type=int, default=None, help="Download only initial N bytes")
    args = parser.parse_args()

    try:
        download_txd22(args.output, verify=not args.no_verify, sample_bytes=args.sample_bytes)
    except Exception as exc:
        print(f"Error downloading TXD-22: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

