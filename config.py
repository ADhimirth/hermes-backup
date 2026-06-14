"""
Plugin configuration for hermes-backup.

Loads config from ~/.hermes/plugins/hermes-backup/config.yaml
with env var overrides.
"""

import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # fallback — no YAML module, use env vars only

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load() -> dict:
    """Load plugin configuration."""
    cfg: dict = {
        "provider": "s3",
        "enabled": True,
        "auto_backup": False,
        "auto_backup_scope": "config",
        "max_retention_days": 30,
        "provider_config": {},
    }

    if yaml and CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            file_cfg = yaml.safe_load(f) or {}
            cfg.update(file_cfg)

    # Env var overrides
    if os.environ.get("HERMES_BACKUP_PROVIDER"):
        cfg["provider"] = os.environ["HERMES_BACKUP_PROVIDER"]

    # Provider-specific env overrides
    provider_cfg = cfg.setdefault("provider_config", {})
    if os.environ.get("HERMES_BACKUP_S3_BUCKET"):
        provider_cfg["bucket"] = os.environ["HERMES_BACKUP_S3_BUCKET"]
    if os.environ.get("AWS_DEFAULT_REGION"):
        provider_cfg["region"] = os.environ["AWS_DEFAULT_REGION"]
    if os.environ.get("HERMES_BACKUP_S3_PREFIX"):
        provider_cfg["prefix"] = os.environ["HERMES_BACKUP_S3_PREFIX"]

    return cfg