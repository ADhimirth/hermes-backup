"""
AWS S3 backup provider — built-in storage backend for hermes-backup.

Requires: boto3, HERMES_S3_BUCKET env var.
Optionally: HERMES_S3_PREFIX (default: "hermes-backup/"), AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
"""

import json
import os

from . import BaseBackupProvider, register_provider


class S3BackupProvider(BaseBackupProvider):
    name = "s3"

    def _get_client(self):
        import boto3
        return boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )

    def _get_bucket(self) -> str:
        bucket = os.environ.get("HERMES_S3_BUCKET", "")
        if not bucket:
            raise ValueError("HERMES_S3_BUCKET environment variable not set")
        return bucket

    def _get_prefix(self) -> str:
        return os.environ.get("HERMES_S3_PREFIX", "hermes-backup/")

    def run_backup(self, scope: str = "full") -> str:
        import datetime
        from pathlib import Path

        hermes_home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_key = f"{self._get_prefix()}{timestamp}/"

        # Map scope to files to back up
        scope_map = {
            "config": ["config.yaml", ".env", "auth.json"],
            "state": ["state.db"],
            "skills": ["skills/"],
            "profiles": ["profiles/"],
            "full": ["config.yaml", ".env", "auth.json", "state.db", "skills/", "profiles/"],
        }

        files_to_backup = scope_map.get(scope, scope_map["full"])
        client = self._get_client()
        bucket = self._get_bucket()

        uploaded = []
        for rel_path in files_to_backup:
            full_path = os.path.join(hermes_home, rel_path)
            if os.path.isfile(full_path):
                key = f"{snapshot_key}{rel_path}"
                client.upload_file(full_path, bucket, key)
                uploaded.append(rel_path)
            elif os.path.isdir(full_path):
                for root, _dirs, files in os.walk(full_path):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        rel = os.path.relpath(fpath, hermes_home)
                        key = f"{snapshot_key}{rel}"
                        client.upload_file(fpath, bucket, key)
                        uploaded.append(rel)

        return json.dumps({
            "status": "ok",
            "snapshot": snapshot_key,
            "files": len(uploaded),
            "scope": scope,
            "bucket": bucket,
        })

    def list_snapshots(self) -> str:
        import boto3
        client = self._get_client()
        bucket = self._get_bucket()
        prefix = self._get_prefix()

        paginator = client.get_paginator("list_objects_v2")
        snapshots = {}
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            for cp in page.get("CommonPrefixes", []):
                snapshots[cp["Prefix"]] = {"prefix": cp["Prefix"]}

        return json.dumps({
            "snapshots": [
                {"name": s.replace(prefix, "").rstrip("/"), "path": s}
                for s in sorted(snapshots.keys(), reverse=True)
            ]
        })

    def restore_snapshot(self, snapshot: str, scope: str = "full") -> str:
        from pathlib import Path

        hermes_home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
        snapshot_prefix = f"{self._get_prefix()}{snapshot}/" if "/" not in snapshot else snapshot
        if not snapshot_prefix.endswith("/"):
            snapshot_prefix += "/"

        client = self._get_client()
        bucket = self._get_bucket()

        paginator = client.get_paginator("list_objects_v2")
        restored = []
        for page in paginator.paginate(Bucket=bucket, Prefix=snapshot_prefix):
            for obj in page.get("Contents", []):
                rel_path = obj["Key"].replace(snapshot_prefix, "")
                target = os.path.join(hermes_home, rel_path)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                client.download_file(bucket, obj["Key"], target)
                restored.append(rel_path)

        return json.dumps({
            "status": "ok",
            "snapshot": snapshot_prefix,
            "files_restored": len(restored),
        })

    def status(self) -> str:
        bucket = os.environ.get("HERMES_S3_BUCKET", "not set")
        return json.dumps({
            "provider": self.name,
            "bucket": bucket,
            "prefix": self._get_prefix(),
            "ok": True,
        })


def register() -> None:
    register_provider(S3BackupProvider())


register()