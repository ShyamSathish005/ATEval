# Operating-system installation notes

Follow the shared [installation guide](installation.md) after installing the
listed system tools.

## macOS

Install Python 3.11+ and Node.js 22 (for building the UI) using an approved
package manager or official installers. For container use, install Docker
Desktop. In Terminal, create/activate a Python virtual environment and run
the native commands in the main installation guide. The API listens only on
`127.0.0.1` by default.

## Windows

Install Python 3.11+ and Node.js 22 from official installers and enable the
Python launcher. In PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[ui-server,writing-docs]"
python -m ateval doctor
```

If script activation is restricted, use the Python executable inside `.venv`
directly instead of weakening the system execution policy. Docker Desktop is
optional.

## Linux

Install Python 3.11+, its venv/pip support, Node.js 22, and optionally Docker
Engine plus the Compose plugin from your distribution or vendor repository.
Create a virtual environment and follow the native setup commands. Keep the
API bound to loopback unless deliberately configuring a reviewed deployment.

Cross-platform installation has not yet been verified in clean macOS,
Windows, and Linux environments. Report issues with OS and version details,
but do not attach manuscript files or private data.
