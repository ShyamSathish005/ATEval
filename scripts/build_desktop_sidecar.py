#!/usr/bin/env python3
"""Build the standalone PyInstaller sidecar binary for the ATEval desktop application."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_target_triple() -> str:
    """Return the Tauri-compatible target triple for the current host."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        arch = "aarch64" if machine in {"arm64", "aarch64"} else "x86_64"
        return f"{arch}-apple-darwin"
    elif system == "linux":
        arch = "aarch64" if machine in {"arm64", "aarch64"} else "x86_64"
        return f"{arch}-unknown-linux-gnu"
    elif system == "windows":
        arch = "aarch64" if machine in {"arm64", "aarch64"} else "x86_64"
        return f"{arch}-pc-windows-msvc.exe"
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")


def build_sidecar(
    output_dir: Path | None = None,
    target_triple: str | None = None,
    clean_build: bool = True,
    verify: bool = True,
) -> Path:
    triple = target_triple or get_target_triple()
    out_dir = output_dir or (PROJECT_ROOT / "src-tauri" / "binaries")
    out_dir.mkdir(parents=True, exist_ok=True)

    binary_name = f"ateval-api-{triple}"
    entry_point = PROJECT_ROOT / "ateval" / "desktop_sidecar.py"
    build_dir = PROJECT_ROOT / "build" / "pyinstaller"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name",
        binary_name,
        "--distpath",
        str(out_dir),
        "--workpath",
        str(build_dir / "work"),
        "--specpath",
        str(build_dir),
        # Collect runtime dependencies
        "--collect-all",
        "uvicorn",
        "--collect-all",
        "fastapi",
        "--collect-all",
        "starlette",
        "--collect-all",
        "pydantic",
        "--collect-all",
        "pydantic_core",
        "--collect-all",
        "ateval",
        # Explicit exclusions for heavy non-desktop research dependencies
        "--exclude-module",
        "torch",
        "--exclude-module",
        "transformers",
        "--exclude-module",
        "spacy",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "ruff",
        "--exclude-module",
        "pip_audit",
        "--exclude-module",
        "cyclonedx_bom",
        str(entry_point),
    ]

    print(f"Building sidecar binary: {binary_name} -> {out_dir}")
    start_time = time.time()
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    subprocess.run(cmd, check=True, env=env)
    elapsed = time.time() - start_time

    binary_path = out_dir / binary_name
    if not binary_path.is_file():
        # On Windows it may have appended .exe
        alt = out_dir / f"{binary_name}.exe"
        if alt.is_file():
            binary_path = alt
        else:
            raise FileNotFoundError(f"PyInstaller did not generate expected binary at {binary_path}")

    # Ensure executable permissions on POSIX
    if os.name != "nt":
        binary_path.chmod(0o755)

    size_mb = binary_path.stat().st_size / (1024 * 1024)
    print(f"Build completed in {elapsed:.1f}s. Size: {size_mb:.2f} MiB -> {binary_path}")

    if verify:
        verify_sidecar(binary_path)

    return binary_path


def verify_sidecar(binary_path: Path) -> None:
    """Run an automated verification smoke test on the built standalone sidecar executable."""
    print(f"Verifying standalone sidecar binary: {binary_path}")

    # 1. Verify --help
    help_res = subprocess.run([str(binary_path), "--help"], capture_output=True, text=True, check=True)
    assert "ateval-desktop-sidecar" in help_res.stdout, "Help output missing expected program name"

    # 2. Verify launch, readiness handshake, and graceful shutdown
    env = {
        **os.environ,
        "ATEVAL_HOME": str(PROJECT_ROOT / ".ateval-verify-smoke"),
        "no_proxy": "127.0.0.1,localhost",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    t0 = time.time()
    proc = subprocess.Popen(
        [str(binary_path), "--port", "0"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        first_line = proc.stdout.readline()
        startup_latency = time.time() - t0
        if not first_line:
            stderr_out = proc.stderr.read() if proc.stderr else ""
            raise AssertionError(f"Sidecar process terminated without emitting readiness handshake. Stderr: {stderr_out}")
        event = json.loads(first_line.strip())
        assert event.get("event") == "ready", f"Unexpected handshake event: {event}"
        assert event.get("protocol_version") == "1.0"
        port = int(event["port"])
        print(f"Sidecar started in {startup_latency:.2f}s on 127.0.0.1:{port} (pid {event['pid']})")

        # Query health endpoint with retry
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/health")
        last_err = None
        for _ in range(15):
            try:
                with opener.open(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode())
                    assert data.get("status") == "ok", f"Health check failed: {data}"
                    last_err = None
                    break
            except Exception as e:
                last_err = e
                time.sleep(0.2)
        if last_err is not None:
            raise last_err

        # Close stdin to trigger graceful watchdog shutdown
        assert proc.stdin is not None
        proc.stdin.close()
        proc.wait(timeout=5.0)
        assert proc.returncode == 0, f"Sidecar exited with code {proc.returncode}"
        print("Sidecar shutdown cleanly upon stdin closure (EOF).")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2.0)
        shutil.rmtree(PROJECT_ROOT / ".ateval-verify-smoke", ignore_errors=True)

    print(f"Verification PASSED for {binary_path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for sidecar binary")
    parser.add_argument("--target-triple", default=None, help="Override target triple (defaults to host triple)")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification smoke test")
    args = parser.parse_args()

    build_sidecar(
        output_dir=args.output_dir,
        target_triple=args.target_triple,
        verify=not args.no_verify,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
