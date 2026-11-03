#!/usr/bin/env python3
"""Exercise the packaged application after a clean dependency installation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8765"


def request(path: str, *, data: bytes | None = None, method: str = "GET", headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers or {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read()


def multipart(filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = "ATEVAL-CI-SMOKE"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def main() -> int:
    env = {**os.environ, "ATEVAL_HOME": os.path.join(os.getcwd(), ".ateval-ci-smoke")}
    process = subprocess.Popen(
        [sys.executable, "-m", "ateval", "api", "--host", "127.0.0.1", "--port", "8765"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(30):
            try:
                health = json.loads(request("/api/v1/health"))
                if health.get("status") == "ok":
                    break
            except (OSError, ValueError, urllib.error.URLError):
                time.sleep(1)
        else:
            output = process.stdout.read().decode(errors="replace") if process.stdout else ""
            raise RuntimeError(f"API did not become healthy: {output}")

        assert b"<html" in request("/")
        body, content_type = multipart(
            "synthetic.tex",
            b"\\documentclass{article}\\begin{document}Synthetic manuscript text.\\end{document}",
        )
        result = json.loads(request("/api/v1/manuscripts/analyze", data=body, method="POST", headers={"Content-Type": content_type}))
        assert result["document"]["format"] == "tex"
        print("cross-platform packaged install smoke: passed")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
