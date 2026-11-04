"""Integration and validation tests for ATEval M7 desktop packaging."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAURI_DIR = PROJECT_ROOT / "src-tauri"


def test_tauri_config_structure() -> None:
    """Verify tauri.conf.json has all required desktop configurations and security constraints."""
    config_file = TAURI_DIR / "tauri.conf.json"
    assert config_file.is_file(), f"Missing {config_file}"

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert config.get("productName") == "ATEval Academic Revision"
    assert config.get("identifier") == "com.ateval.academic-revision"

    build_cfg = config.get("build", {})
    assert build_cfg.get("frontendDist") == "../frontend/dist/client"

    app_cfg = config.get("app", {})
    security_cfg = app_cfg.get("security", {})
    csp = security_cfg.get("csp", "")
    assert "default-src 'self'" in csp
    # Frontend must not have unsafe-eval
    assert "'unsafe-eval'" not in csp

    bundle_cfg = config.get("bundle", {})
    assert bundle_cfg.get("active") is True
    external_bins = bundle_cfg.get("externalBin", [])
    assert any("ateval-api" in b for b in external_bins), f"externalBin missing ateval-api: {external_bins}"


def test_tauri_capabilities_least_privilege() -> None:
    """Verify frontend capabilities strictly enforce least-privilege without arbitrary shell execution."""
    cap_file = TAURI_DIR / "capabilities" / "default.json"
    assert cap_file.is_file(), f"Missing {cap_file}"

    with open(cap_file, "r", encoding="utf-8") as f:
        cap = json.load(f)

    perms = cap.get("permissions", [])
    assert "core:default" in perms
    # Shell commands must NOT be exposed to the webview
    assert "shell:allow-execute" not in perms
    assert "shell:allow-spawn" not in perms
    assert "shell:default" not in perms


def test_desktop_icons_existence_and_sizes() -> None:
    """Verify desktop application icons are generated in all required formats."""
    icons_dir = TAURI_DIR / "icons"
    assert icons_dir.is_dir(), f"Missing {icons_dir}"

    required_icons = [
        "32x32.png",
        "128x128.png",
        "128x128@2x.png",
        "icon.png",
        "icon.ico",
        "icon.icns",
    ]
    for icon_name in required_icons:
        icon_path = icons_dir / icon_name
        assert icon_path.is_file(), f"Missing required icon {icon_name}"
        assert icon_path.stat().st_size > 0, f"Icon {icon_name} is empty"


def test_sidecar_binary_ready_and_executable() -> None:
    """Verify PyInstaller built sidecar binary exists, is executable, and is located for aarch64."""
    bin_dir = TAURI_DIR / "binaries"
    assert bin_dir.is_dir()

    expected_binary = bin_dir / "ateval-api-aarch64-apple-darwin"
    if not expected_binary.is_file():
        pytest.skip("Binary ateval-api-aarch64-apple-darwin not yet built on this runner")

    mode = expected_binary.stat().st_mode
    is_executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    assert is_executable, f"Sidecar binary {expected_binary} is not executable"
    assert expected_binary.stat().st_size > 50 * 1024 * 1024, "Sidecar binary is suspiciously small (<50MB)"


def test_frontend_dist_contains_required_assets() -> None:
    """Verify the frontend distribution folder has built client assets ready for Tauri packaging."""
    dist_client = PROJECT_ROOT / "frontend" / "dist" / "client"
    if not dist_client.is_dir():
        pytest.skip("frontend/dist/client not built yet on this test runner")
    assert (dist_client / "index.html").is_file(), "index.html missing from dist/client"
    assets_dir = dist_client / "assets"
    assert assets_dir.is_dir(), "dist/client/assets missing"
    js_files = list(assets_dir.glob("*.js"))
    assert len(js_files) > 0, "No JS files found in dist/client/assets"
    css_files = list(assets_dir.glob("*.css"))
    assert len(css_files) > 0, "No CSS files found in dist/client/assets"
