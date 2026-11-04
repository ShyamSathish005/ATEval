"""Dedicated desktop sidecar entry point for ATEval Tauri integration.

Starts the existing FastAPI application on loopback only with safe ephemeral port
negotiation, per-launch token validation, and a versioned readiness handshake.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import sys
import threading
from typing import Any

LOG = logging.getLogger("ateval.desktop")


def allocate_loopback_socket(preferred_port: int = 0) -> tuple[socket.socket, int]:
    """Bind a real TCP socket to 127.0.0.1 without closing it, preventing port race conditions."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", preferred_port))
    actual_port = sock.getsockname()[1]
    return sock, actual_port


def emit_handshake(host: str, port: int, protocol_version: str = "1.0") -> None:
    """Emit a single-line machine-readable readiness event to stdout. Never logs tokens."""
    event = {
        "event": "ready",
        "protocol_version": protocol_version,
        "host": host,
        "port": port,
        "pid": os.getpid(),
    }
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def _stdin_watchdog(shutdown_event: threading.Event) -> None:
    """Watch stdin; when the parent process exits, the stdin pipe closes (EOF)."""
    try:
        while not shutdown_event.is_set():
            line = sys.stdin.readline()
            if not line:  # EOF -> parent closed pipe
                break
    except Exception:
        pass
    finally:
        if not shutdown_event.is_set():
            # Signal server exit
            shutdown_event.set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ateval-desktop-sidecar",
        description="ATEval desktop sidecar runtime",
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "0")), help="Bind port; 0 selects an ephemeral port (default)")
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "localhost"), help="Bind host (loopback only)")
    parser.add_argument("--token-stdin", action="store_true", help="Read per-launch token from the first line of stdin")
    parser.add_argument("--require-token", action="store_true", default=True, help="Enforce per-launch token for state changes (default: True)")
    parser.add_argument("--log-level", default="warning", choices=("debug", "info", "warning", "error"))

    args = parser.parse_args(argv)

    if args.token_stdin:
        # Read token securely from stdin first line before watchdog
        token_line = sys.stdin.readline().strip()
        if token_line:
            os.environ["ATEVAL_LAUNCH_TOKEN"] = token_line

    if args.require_token:
        os.environ["ATEVAL_REQUIRE_LAUNCH_TOKEN"] = "1"
        os.environ["ATEVAL_REQUIRE_ORIGIN_FOR_MUTATIONS"] = "0"  # Desktop requests may originate from tauri:// or loopback

    # Import API after environment setup so security constants bind correctly
    from ateval import api as local_api
    import uvicorn

    sock, port = allocate_loopback_socket(args.port)

    shutdown_event = threading.Event()
    watchdog = threading.Thread(target=_stdin_watchdog, args=(shutdown_event,), daemon=True)
    watchdog.start()

    config = uvicorn.Config(
        local_api.app,
        host=args.host,
        port=port,
        log_level=args.log_level,
        access_log=False,
    )
    server = uvicorn.Server(config)

    def handle_signal(sig, frame):
        server.should_exit = True
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Watchdog poller to stop server if stdin EOF received
    def check_shutdown():
        while not shutdown_event.is_set():
            shutdown_event.wait(0.5)
        server.should_exit = True

    poll_thread = threading.Thread(target=check_shutdown, daemon=True)
    poll_thread.start()

    # Emit readiness handshake immediately before entering uvicorn run loop
    emit_handshake(args.host, port)

    try:
        server.run(sockets=[sock])
    finally:
        try:
            sock.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
