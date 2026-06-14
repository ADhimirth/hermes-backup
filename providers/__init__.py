"""
BaseBackupProvider — abstract interface for backup storage backends.

All providers inherit from BaseBackupProvider and implement:
  - name (property)
  - upload(path, key)  -> str (remote key / url)
  - list(prefix)       -> list[dict]
  - download(key, dest) -> str (local path)
  - delete(key)        -> bool
  - test_connection()  -> bool
"""

import abc
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class BackupEntry:
    """Metadata for a single backup artifact."""

    def __init__(
        self,
        key: str,
        size_bytes: int,
        created_at: Optional[str] = None,
        source_path: Optional[str] = None,
    ):
        self.key = key
        self.size_bytes = size_bytes
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.source_path = source_path

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "source_path": self.source_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BackupEntry":
        return cls(
            key=d["key"],
            size_bytes=d.get("size_bytes", 0),
            created_at=d.get("created_at"),
            source_path=d.get("source_path"),
        )


class BaseBackupProvider(abc.ABC):
    """Abstract base class for backup storage providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 's3', 'gdrive')."""
        ...

    @abc.abstractmethod
    def upload(self, local_path: str, remote_key: str) -> str:
        """
        Upload a local file to remote storage.
        Returns the remote key on success.
        Raises BackupError on failure.
        """
        ...

    @abc.abstractmethod
    def list(self, prefix: str = "") -> list[BackupEntry]:
        """
        List backups under an optional prefix.
        Returns sorted list of BackupEntry (newest first).
        """
        ...

    @abc.abstractmethod
    def download(self, remote_key: str, dest_path: str) -> str:
        """
        Download a remote backup to a local path.
        Returns the local path on success.
        """
        ...

    @abc.abstractmethod
    def delete(self, remote_key: str) -> bool:
        """
        Delete a remote backup by key.
        Returns True if deleted, False if not found.
        """
        ...

    @abc.abstractmethod
    def test_connection(self) -> bool:
        """Test whether the storage backend is reachable and configured."""
        ...


class BackupError(Exception):
    """Raised when a backup operation fails."""


def load_provider(provider_name: str, config: dict) -> BaseBackupProvider:
    """
    Factory: load a provider by name.
    Built-in: 's3'. Others can be registered via entry points.
    """
    if provider_name == "s3":
        from .s3 import S3BackupProvider

        return S3BackupProvider(config)
    raise BackupError(f"Unknown backup provider: {provider_name}")