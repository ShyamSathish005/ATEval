"""TOML configuration loading with conservative defaults and validation."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class AppConfig:
    seed: int = 17
    offline: bool = True
    log_level: str = "INFO"
    output_dir: str = "runs"


def load_config(path: str | Path | None = None) -> AppConfig:
    if path is None:
        return AppConfig()
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)
    app = raw.get("app", {})
    cfg = AppConfig(**{key: app[key] for key in AppConfig.__dataclass_fields__ if key in app})
    if cfg.seed < 0:
        raise ValueError("app.seed must be non-negative")
    if not cfg.output_dir.strip():
        raise ValueError("app.output_dir must not be empty")
    return cfg
