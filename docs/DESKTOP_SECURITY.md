# ATEval Desktop Security Review

## 1. Threat Model & Security Posture

ATEval Desktop is designed under a **strict local-first, zero-trust** security model. Academic manuscripts often contain unpublished pre-print research, sensitive participant data, or confidential intellectual property. The application must guarantee that:
1. No manuscript text is transmitted to external cloud servers.
2. Web content rendered inside the WebView cannot execute arbitrary shell commands.
3. Other local applications running on the user's computer cannot query or manipulate the ATEval API server without authorization.

---

## 2. Core Security Controls

### 2.1 Content Security Policy (CSP)
Defined in `src-tauri/tauri.conf.json`:
```
default-src 'self' ipc: http://ipc.localhost; img-src 'self' asset: http://asset.localhost data:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self' http://127.0.0.1:* http://localhost:*
```
- **Disallows `unsafe-eval`**: Evaluated code strings and dynamic code generation are completely banned.
- **Restricts `connect-src`**: Network requests can only be dispatched to same-origin IPC and local loopback interfaces (`127.0.0.1`, `localhost`).
- **No external script sources**: No remote CDN scripts or analytics trackers can be loaded.

### 2.2 IPC Least Privilege & Shell Sandboxing
Defined in `src-tauri/capabilities/default.json`:
```json
{
  "identifier": "default",
  "windows": ["main"],
  "permissions": [
    "core:default"
  ]
}
```
- **Dangerous permissions stripped**: `shell:allow-execute`, `shell:allow-spawn`, and `shell:default` are **explicitly excluded** from the window capability.
- **Native command isolation**: The frontend webview cannot spawn child processes. All sidecar management is encapsulated strictly within the Rust native layer (`src-tauri/src/lib.rs`).
- The only IPC command exposed to the webview is `get_backend_connection`, which returns read-only connection credentials.

### 2.3 Ephemeral Launch Token Authentication
- Upon startup, the Tauri native host generates a cryptographically random 32-byte (64-character hex) token using `rand::thread_rng().fill_bytes(&mut bytes)`.
- The token is passed to the sidecar process via `ATEVAL_LAUNCH_TOKEN`.
- The frontend retrieves this token via `get_backend_connection` and injects it as `X-ATEval-Token` on all non-health HTTP and WebSocket requests.
- Any request from another unauthorized process on the machine lacking this token is rejected with `401 Unauthorized` or `403 Forbidden`.
- Tokens are never written to disk or logged to console logs.

### 2.4 Ephemeral Loopback Port Pre-Binding
- In `ateval/desktop_sidecar.py`, a real TCP socket is pre-bound to `("127.0.0.1", 0)`.
- The operating system assigns an available ephemeral port from the dynamic range.
- Passing the live socket object directly to `uvicorn.Server.run(sockets=[sock])` eliminates Time-Of-Check to Time-Of-Use (TOCTOU) port hijacking races.
- The service binds strictly to `127.0.0.1` and never to `0.0.0.0`, preventing exposure to the local area network.

### 2.5 Watchdog Process Termination
- The sidecar runs a background daemon thread monitoring standard input (`sys.stdin.read(1)`).
- If the parent Tauri process terminates, crashes, or is killed by the OS, the stdin pipe closes with EOF.
- The watchdog immediately triggers `os._exit(0)` to guarantee zero orphaned Python processes consuming system resources.
- On standard application shutdown, Tauri's `RunEvent::Exit` handler explicitly kills the child process.
