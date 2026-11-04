# ATEval Desktop Installation & Build Guide

## 1. System Requirements

- **macOS Apple Silicon (Primary PoC)**: macOS 12 Monterey or newer on Apple Silicon (M1/M2/M3/M4, `aarch64-apple-darwin`).
- **RAM**: 8 GB minimum, 16 GB recommended (especially when running local Ollama LLMs).
- **Disk Space**: ~300 MB for the ATEval Desktop application bundle. Additional 2–4 GB for optional local Ollama models.

---

## 2. End-User Installation

### macOS Apple Silicon (`.dmg`)
1. Download `ATEval-Academic-Revision_0.1.0_aarch64.dmg`.
2. Double-click the `.dmg` to mount the disk image.
3. Drag **ATEval Academic Revision.app** to your **Applications** folder.
4. Launch ATEval from Applications or Spotlight.
5. On first launch, the **First-Run Onboarding Guide** will appear, displaying:
   - Backend sidecar service status (connected on loopback).
   - Local Ollama AI model status.
   - Recommended command to start your local revision model:
     ```bash
     ollama run ateval-xtragpt-1_5b-q8_0
     ```

---

## 3. Developer Build Instructions

### Prerequisites
- Python 3.11+ with `pip`
- Node.js 20+ with `npm`
- Rust 1.77+ and `cargo`
- macOS Command Line Tools: `xcode-select --install`

### Step 1: Install Python Dependencies & Build Sidecar
```bash
# In project root
python3 -m pip install -e .
python3 -m pip install pyinstaller

# Build the standalone PyInstaller sidecar binary
python3 scripts/build_desktop_sidecar.py
```
This builds `src-tauri/binaries/ateval-api-aarch64-apple-darwin` (~226 MB) with all non-essential training dependencies (`torch`, `transformers`, `spacy`, `pytest`) excluded.

### Step 2: Build Frontend Assets
```bash
cd frontend
npm install
npm run build
```
This produces optimized production assets in `frontend/dist/client/`.

### Step 3: Generate Desktop Icons (if modifying)
```bash
python3 scripts/generate_desktop_icons.py
```
This outputs all standard PNG sizes, multi-resolution `icon.ico`, and `icon.icns`.

### Step 4: Build Tauri Native Application
```bash
cd frontend
npx tauri build
```
The native application bundle (`.app`) and disk image (`.dmg`) will be placed in:
`src-tauri/target/release/bundle/macos/` and `src-tauri/target/release/bundle/dmg/`.

---

## 4. Verification & Testing

Run the full automated desktop test suite:
```bash
# Test sidecar entry point, dynamic port binding, and watchdog
python3 -m pytest tests/test_desktop_sidecar.py

# Test Tauri configuration, capabilities, icons, and binary executable
python3 -m pytest tests/test_desktop_packaging.py

# Test frontend static site routing
cd frontend && npm run test:sites
```
