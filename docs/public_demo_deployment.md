# Public demonstration deployment

`render.yaml` describes a small Docker-based Render service intended only for
a public synthetic example. It is not the local research service. The public
mode is read-only except for a rate-limited endpoint that analyzes one fixed,
synthetic TeX fixture embedded in ATEval. It rejects manuscript uploads,
dataset imports, edits, and persistent state changes before route parsing.
No model endpoint is configured. The service uses ephemeral storage and
disables automatic deploys.

The container reads its listen port from `PORT` (default 8000 for local use).
Render requires a web service to bind `0.0.0.0` and its injected `PORT`, which
defaults to 10000; TLS terminates at Render's edge before traffic reaches the
container. The app uses the explicit HTTPS origin and configured hostname for
same-origin validation. See the [Render web service](https://render.com/docs/web-services)
and [environment variable](https://render.com/docs/environment-variables) documentation.

The browser UI identifies public mode, disables the file picker and editing
controls, and offers only the synthetic example. The service permits same-
origin requests on the explicit Render hostname and allows 20 API requests
per client per minute in one process. On Render it keys by the first
`X-Forwarded-For` address inserted by the platform edge; elsewhere it uses the
socket peer. This in-memory limiter is a demonstration guard, not a distributed
denial-of-service defense. Render documents that its app sees a proxy address
by default and that the client address is carried in `X-Forwarded-For`; verify
the header behavior for the deployed service and reject untrusted direct access.
The Render plan provides resource limits; add platform-level abuse protection
before public exposure.

Before deploying, confirm the generated public hostname matches the exact
host and origin configured in `render.yaml`, and review current Render ingress,
retention, logging, and resource policies. Do not add a persistent disk, model
endpoint, arbitrary upload route, or user account/state feature without a new
security/privacy review. The demo must not accept confidential, unpublished,
personal, or restricted manuscripts.

No Render deployment has been launched from this workspace. A future deployment
requires an isolated ATEval repository and a passing release CI gate.
