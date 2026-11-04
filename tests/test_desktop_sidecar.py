"""Unit and lifecycle tests for the ATEval desktop sidecar."""

from __future__ import annotations

import io
import json
import os
import signal
import subprocess
import sys
import time
import unittest
import urllib.request
from unittest.mock import patch

from ateval.desktop_sidecar import allocate_loopback_socket, emit_handshake


class DesktopSidecarTests(unittest.TestCase):
    def test_allocate_loopback_socket_returns_bound_socket_and_port(self):
        sock, port = allocate_loopback_socket(0)
        try:
            self.assertGreater(port, 1024)
            self.assertLessEqual(port, 65535)
            host, bound_port = sock.getsockname()[:2]
            self.assertEqual(host, "127.0.0.1")
            self.assertEqual(bound_port, port)
        finally:
            sock.close()

    def test_emit_handshake_emits_valid_json_ready_event(self):
        stream = io.StringIO()
        with patch("sys.stdout", stream):
            emit_handshake("127.0.0.1", 54321, protocol_version="1.0")
        output = stream.getvalue()
        self.assertTrue(output.endswith("\n"))
        data = json.loads(output)
        self.assertEqual(data["event"], "ready")
        self.assertEqual(data["protocol_version"], "1.0")
        self.assertEqual(data["host"], "127.0.0.1")
        self.assertEqual(data["port"], 54321)
        self.assertEqual(data["pid"], os.getpid())

    def test_sidecar_subprocess_handshake_and_stdin_eof_shutdown(self):
        env = {
            **os.environ,
            "ATEVAL_HOME": os.path.join(os.getcwd(), ".ateval-desktop-test"),
            "no_proxy": "127.0.0.1,localhost",
            "NO_PROXY": "127.0.0.1,localhost",
        }
        process = subprocess.Popen(
            [sys.executable, "-m", "ateval.desktop_sidecar", "--port", "0"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Read first line from stdout which must be the readiness handshake
            first_line = process.stdout.readline()
            if not first_line:
                stderr_out = process.stderr.read()
                self.fail(f"Sidecar process exited without emitting handshake: {stderr_out}")
            handshake = json.loads(first_line.strip())
            self.assertEqual(handshake["event"], "ready")
            self.assertEqual(handshake["host"], "127.0.0.1")
            port = handshake["port"]
            self.assertGreater(port, 1024)

            # Health check via loopback with retry
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/health")
            last_err = None
            for _ in range(15):
                try:
                    with opener.open(req, timeout=3.0) as resp:
                        self.assertEqual(resp.status, 200)
                        body = json.loads(resp.read().decode())
                        self.assertEqual(body["status"], "ok")
                        last_err = None
                        break
                except Exception as e:
                    last_err = e
                    time.sleep(0.2)
            if last_err is not None:
                raise last_err

            # Closing stdin simulates parent process exit -> sidecar watchdog detects EOF and shuts down
            process.stdin.close()
            exit_code = process.wait(timeout=5.0)
            self.assertEqual(exit_code, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2.0)
            import shutil
            shutil.rmtree(os.path.join(os.getcwd(), ".ateval-desktop-test"), ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
