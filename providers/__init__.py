"""
Backup provider interface and registry.

Each provider implements the BaseBackupProvider interface.
Register new providers here.
"""

import json
import importlib
import os
from typing import Optional


class BaseBackupProvider:
    """Interface all backup providers must implement."""

    name: str = "base"

    def run_backup(self, scope: str = "full") -> str:
        raise NotImplementedError

    def list_snapshots(self) -> str:
        raise NotImplementedError

    def restore_snapshot(self, snapshot: str, scope: str = "full") -> str:
        raise NotImplementedError

    def status(self) -> str:
        return json.dumps({"provider": self.name, "ok": True})


_PROVIDERS: dict[str, BaseBackupProvider] = {}


def register_provider(provider: BaseBackupProvider) -> None:
    _PROVIDERS[provider.name] = provider


def get_provider() -> Optional[BaseBackupProvider]:
    """Resolve the configured provider by name."""
    name = os.environ.get("HERMES_BACKUP_PROVIDER", "").strip().lower()
    if not name:
        name = "s3"  # default

    if name in _PROVIDERS:
        return _PROVIDERS[name]

    # Lazy-import provider modules
    try:
        mod = importlib.import_module(f".{name}", __package__)
        if hasattr(mod, "register"):
            mod.register()
        return _PROVIDERS.get(name)
    except ImportError:
        return None


# Built-in providers auto-register on import
from . import s3  # noqa: E402, F811