"""
Tool handlers for hermes-backup plugin.

Each handler is a function with signature:
    def handler(args: dict, **kwargs) -> str

Always return a JSON string (success or error).
Never raise exceptions — catch everything and return error JSON.
"""

import json
import os
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config as plugin_config
from .providers import load_provider, BackupError

HERMES_HOME = Path.home() / ".hermes"


def _get_provider():
    """Load the configured provider (cached in plugin config)."""
    cfg = plugin_config.load()
    return load_provider(cfg.get("provider", "s3"), cfg.get("provider_config", {}))


# ── Backup scopes ────────────────────────────────────────────────────

SCOPE_PATHS = {
    "config": ["config.yaml"],
    "state": ["state.db"],
    "skills": ["skills/"],
    "profiles": ["profiles/"],
    "kanban": ["kanban.db"],
}

DEFAULT_SCOPE = ["config", "state", "skills", "profiles", "kanban"]


def _resolve_scope(scope_str: str) -> list[str]:
    """Parse a scope string like 'all', 'config', or 'config,skills'."""
    if not scope_str or scope_str == "all":
        return DEFAULT_SCOPE
    return [s.strip() for s in scope_str.split(",") if s.strip()]


def _collect_files(scopes: list[str]) -> list[tuple[str, str]]:
    """
    Given a list of scope names, return [(relative_path, abs_path), ...]
    relative_path is the path *inside* the backup archive.
    """
    files = []
    seen = set()

    for scope in scopes:
        for pattern in SCOPE_PATHS.get(scope, []):
            path = HERMES_HOME / pattern
            if path.is_file():
                if path not in seen:
                    seen.add(path)
                    files.append((str(path.relative_to(HERMES_HOME)), str(path)))
            elif path.is_dir():
                for fpath in sorted(path.rglob("*")):
                    if fpath.is_file() and fpath not in seen:
                        seen.add(fpath)
                        files.append((str(fpath.relative_to(HERMES_HOME)), str(fpath)))
    return files


# ── Archive helpers ───────────────────────────────────────────────────

def _create_archive(scope_str: str, label: Optional[str] = None) -> str:
    """Create a .tar.gz archive of selected scopes. Returns path to archive."""
    scopes = _resolve_scope(scope_str)
    files = _collect_files(scopes)

    if not files:
        raise BackupError(f"No files matched scope '{scope_str}' — nothing to back up.")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = f"-{label}" if label else ""
    archive_name = f"hermes-backup-{ts}{safe_label}.tar.gz"

    tmp = tempfile.gettempdir()
    archive_path = os.path.join(tmp, archive_name)

    with tarfile.open(archive_path, "w:gz") as tar:
        for rel_path, abs_path in files:
            tar.add(abs_path, arcname=rel_path)

    return archive_path


def _extract_archive(archive_path: str, scope_str: str, dry_run: bool) -> dict:
    """
    Extract an archive, optionally scoping to specific paths.
    Returns dict with summary.
    """
    scopes = _resolve_scope(scope_str)
    scope_patterns = []
    for s in scopes:
        scope_patterns.extend(SCOPE_PATHS.get(s, []))

    restored = []
    skipped = []

    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            # If scope restricts, check prefix
            if scope_patterns:
                matched = any(
                    member.name.startswith(p.rstrip("/")) for p in scope_patterns
                )
                if not matched:
                    skipped.append(member.name)
                    continue

            dest = HERMES_HOME / member.name
            if dry_run:
                restored.append(f"WOULD RESTORE: {dest}")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                tar.extract(member, path=HERMES_HOME)
                restored.append(str(dest))

    return {
        "restored": restored,
        "skipped": skipped,
        "count": len(restored),
        "dry_run": dry_run,
    }


# ── Tool handlers ─────────────────────────────────────────────────────

def backup_now(args: dict, **kwargs) -> str:
    """
    Create an immediate backup.
    CLI alternative: hermes backup now [--scope all] [--label "..."]
    """
    scope_str = args.get("scope", "all")
    label = args.get("label")

    try:
        provider = _get_provider()
        archive_path = _create_archive(scope_str, label)
        archive_name = os.path.basename(archive_path)

        remote_key = provider.upload(archive_path, archive_name)
        os.unlink(archive_path)

        return json.dumps({
            "success": True,
            "remote_key": remote_key,
            "scope": scope_str,
            "label": label,
            "provider": provider.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except BackupError as e:
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        return json.dumps({"success": False, "error": f"Unexpected error: {e}"})


def backup_status(args: dict, **kwargs) -> str:
    """Show backup configuration and provider status."""
    detailed = args.get("detailed", False)

    try:
        cfg = plugin_config.load()
        provider = _get_provider()
        connected = provider.test_connection()

        info = {
            "provider": provider.name,
            "connected": connected,
            "configured_scopes": DEFAULT_SCOPE,
            "config": {
                "enabled": cfg.get("enabled", True),
                "auto_backup": cfg.get("auto_backup", False),
                "max_retention": cfg.get("max_retention_days", 30),
            },
        }

        if connected and detailed:
            backups = provider.list(prefix="")[:3]
            info["recent_backups"] = [b.to_dict() for b in backups]

        return json.dumps({"success": True, "status": info})
    except BackupError as e:
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        return json.dumps({"success": False, "error": f"Unexpected error: {e}"})


def backup_list(args: dict, **kwargs) -> str:
    """List recent backups on the remote provider."""
    limit = args.get("limit", 10)
    prefix = args.get("prefix", "")

    try:
        provider = _get_provider()
        entries = provider.list(prefix=prefix)

        result = {
            "success": True,
            "provider": provider.name,
            "backups": [e.to_dict() for e in entries[:limit]],
            "total": len(entries),
        }
        return json.dumps(result)
    except BackupError as e:
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        return json.dumps({"success": False, "error": f"Unexpected error: {e}"})


def backup_restore(args: dict, **kwargs) -> str:
    """Restore from a backup."""
    key = args.get("key")
    scope_str = args.get("scope", "all")
    dry_run = args.get("dry_run", False)

    try:
        provider = _get_provider()

        if not key:
            # Find the latest backup
            entries = provider.list(prefix="")
            if not entries:
                return json.dumps({"success": False, "error": "No backups found on remote."})
            key = entries[0].key

        tmp = tempfile.gettempdir()
        local_path = os.path.join(tmp, os.path.basename(key))
        provider.download(key, local_path)

        result = _extract_archive(local_path, scope_str, dry_run)
        os.unlink(local_path)

        return json.dumps({
            "success": True,
            "restored_from": key,
            "scope": scope_str,
            "dry_run": dry_run,
            "files_restored": result["count"],
            "details": {
                "restored": result["restored"][:50],  # cap at 50 files
                "skipped": result["skipped"][:20],
            },
        })
    except BackupError as e:
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        return json.dumps({"success": False, "error": f"Unexpected error: {e}"})


# ── Hook handlers ─────────────────────────────────────────────────────

def on_session_end_hook(session_id: str = "", **kwargs) -> None:
    """Auto-backup when a session ends, if enabled."""
    try:
        cfg = plugin_config.load()
        if not cfg.get("auto_backup", False):
            return

        scope = cfg.get("auto_backup_scope", "config")
        provider = _get_provider()

        archive_path = _create_archive(scope, label="auto")
        archive_name = os.path.basename(archive_path)
        provider.upload(archive_path, archive_name)
        os.unlink(archive_path)
    except Exception:
        pass  # Silent — hook failures must never crash the agent


# ── CLI handler ───────────────────────────────────────────────────────

def cli_backup(args: list[str]) -> str:
    """
    CLI entry point: hermes backup <subcommand> [args...]
    Subcommands: now, status, list, restore
    """
    if not args:
        return "Usage: hermes backup [now|status|list|restore] [options]"

    sub = args[0].lower()
    extra = args[1:]

    if sub == "now":
        scope = "all"
        label = None
        for i, a in enumerate(extra):
            if a == "--scope" and i + 1 < len(extra):
                scope = extra[i + 1]
            if a == "--label" and i + 1 < len(extra):
                label = extra[i + 1]
        return backup_now({"scope": scope, "label": label})

    elif sub == "status":
        detailed = "--detailed" in extra or "-d" in extra
        return backup_status({"detailed": detailed})

    elif sub == "list":
        limit = 10
        prefix = ""
        for i, a in enumerate(extra):
            if a == "--limit" and i + 1 < len(extra):
                limit = int(extra[i + 1])
            if a == "--prefix" and i + 1 < len(extra):
                prefix = extra[i + 1]
        return backup_list({"limit": limit, "prefix": prefix})

    elif sub == "restore":
        key = None
        scope = "all"
        dry_run = False
        for i, a in enumerate(extra):
            if a == "--key" and i + 1 < len(extra):
                key = extra[i + 1]
            if a == "--scope" and i + 1 < len(extra):
                scope = extra[i + 1]
            if a == "--dry-run":
                dry_run = True
        return backup_restore({"key": key, "scope": scope, "dry_run": dry_run})

    else:
        return json.dumps({
            "error": f"Unknown subcommand '{sub}'. Try: now, status, list, restore"
        })