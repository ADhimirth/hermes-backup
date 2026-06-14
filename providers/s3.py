"""
S3BackupProvider — backup to AWS S3 (or compatible object storage).

Uses boto3. If boto3 is not installed, the provider raises a descriptive
ImportError at construction time so the plugin can degrade gracefully.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import BackupEntry, BackupError, BaseBackupProvider


def _import_boto3():
    """Lazy-import boto3 so the plugin loads even without it installed."""
    try:
        import boto3  # noqa: F401
    except ImportError:
        raise BackupError(
            "boto3 is not installed. Run: pip install boto3"
        )
    return boto3


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class S3BackupProvider(BaseBackupProvider):
    """Backup provider backed by AWS S3."""

    def __init__(self, config: dict):
        self.bucket = config.get("bucket") or os.environ.get("HERMES_BACKUP_S3_BUCKET", "")
        if not self.bucket:
            raise BackupError(
                "S3 bucket not configured. Set HERMES_BACKUP_S3_BUCKET env var "
                "or pass 'bucket' in config."
            )
        self.prefix = config.get("prefix", "hermes-backups/")
        self.region = config.get("region") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

        # Lazy client — created on first use
        self._client = None

    @property
    def name(self) -> str:
        return "s3"

    @property
    def _s3(self):
        if self._client is None:
            boto3 = _import_boto3()
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def _full_key(self, key: str) -> str:
        return f"{self.prefix.rstrip('/')}/{key.lstrip('/')}"

    def upload(self, local_path: str, remote_key: str) -> str:
        full_key = self._full_key(remote_key)
        try:
            self._s3.upload_file(local_path, self.bucket, full_key)
            return full_key
        except Exception as e:
            raise BackupError(f"S3 upload failed: {e}") from e

    def list(self, prefix: str = "") -> list[BackupEntry]:
        search_prefix = self._full_key(prefix)
        try:
            resp = self._s3.list_objects_v2(Bucket=self.bucket, Prefix=search_prefix)
        except Exception as e:
            raise BackupError(f"S3 list failed: {e}") from e

        contents = resp.get("Contents", [])
        entries = []
        for obj in contents:
            entries.append(
                BackupEntry(
                    key=obj["Key"],
                    size_bytes=obj["Size"],
                    created_at=obj["LastModified"].isoformat(),
                )
            )
        # Newest first
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries

    def download(self, remote_key: str, dest_path: str) -> str:
        full_key = self._full_key(remote_key)
        try:
            os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
            self._s3.download_file(self.bucket, full_key, dest_path)
            return dest_path
        except Exception as e:
            raise BackupError(f"S3 download failed: {e}") from e

    def delete(self, remote_key: str) -> bool:
        full_key = self._full_key(remote_key)
        try:
            self._s3.delete_object(Bucket=self.bucket, Key=full_key)
            return True
        except self._s3.exceptions.NoSuchKey:
            return False
        except Exception as e:
            raise BackupError(f"S3 delete failed: {e}") from e

    def test_connection(self) -> bool:
        try:
            self._s3.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False