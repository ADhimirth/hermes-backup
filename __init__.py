"""
hermes-backup — Multi-storage backup plugin for Hermes Agent.

Registers backup tools, slash commands, and lifecycle hooks.
"""

from pathlib import Path
from typing import Any

PLUGIN_DIR = Path(__file__).parent.resolve()


def register(ctx: Any) -> None:
    """Plugin entry point — called by Hermes on load."""

    # ── Slash Commands ──────────────────────────────────────────────────

    ctx.register_command(
        name="backup",
        handler=_cmd_backup,
        description="Run backup now, list snapshots, restore, or check status",
        args_hint="now | list | restore <snapshot> | status",
    )

    # ── CLI Subcommand ──────────────────────────────────────────────────

    def _setup_backup_cli(subparser) -> None:
        subparser.add_argument("action", choices=["now", "list", "restore", "status"])
        subparser.add_argument("snapshot", nargs="?", help="Snapshot name for restore")

    ctx.register_cli_command(
        name="backup",
        help="Backup Hermes state to cloud storage",
        setup_fn=_setup_backup_cli,
    )

    # ── Lifecycle Hooks ────────────────────────────────────────────────

    ctx.register_hook("on_session_end", _on_session_end)

    # ── Tools ──────────────────────────────────────────────────────────

    ctx.register_tool(
        name="backup_run",
        toolset="tools",
        schema={
            "name": "backup_run",
            "description": "Run a backup of Hermes state to the configured storage provider",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["full", "config", "state", "skills", "profiles"],
                        "description": "What to back up (default: full)",
                    },
                },
            },
        },
        handler=_tool_backup_run,
    )

    ctx.register_tool(
        name="backup_list",
        toolset="tools",
        schema={
            "name": "backup_list",
            "description": "List available backup snapshots from the storage provider",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_tool_backup_list,
    )

    ctx.register_tool(
        name="backup_restore",
        toolset="tools",
        schema={
            "name": "backup_restore",
            "description": "Restore Hermes state from a backup snapshot",
            "parameters": {
                "type": "object",
                "properties": {
                    "snapshot": {
                        "type": "string",
                        "description": "Snapshot ID or name to restore from",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["full", "config", "state", "skills", "profiles"],
                        "description": "Which parts to restore (default: full)",
                    },
                },
                "required": ["snapshot"],
            },
        },
        handler=_tool_backup_restore,
    )

    ctx.register_tool(
        name="backup_status",
        toolset="tools",
        schema={
            "name": "backup_status",
            "description": "Check backup status — last run, next run, storage used",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_tool_backup_status,
    )


# ── Slash Command Handler ──────────────────────────────────────────────


def _cmd_backup(raw_args: str) -> str:
    """Handle /backup slash command."""
    parts = raw_args.strip().split()
    action = parts[0] if parts else "status"

    if action == "now":
        return _tool_backup_run({"scope": "full"})
    elif action == "list":
        return _tool_backup_list({})
    elif action == "restore":
        snapshot = parts[1] if len(parts) > 1 else ""
        return _tool_backup_restore({"snapshot": snapshot})
    else:
        return _tool_backup_status({})


# ── Lifecycle Hook ────────────────────────────────────────────────────


def _on_session_end(**kwargs: Any) -> None:
    """Auto-backup on session end if enabled."""
    import os
    from . import config

    if os.environ.get("HERMES_BACKUP_AUTO", "").lower() in ("1", "true", "yes"):
        _tool_backup_run({"scope": "full"})


# ── Tool Handlers ─────────────────────────────────────────────────────


def _get_provider():
    """Resolve the configured backup provider."""
    from .providers import get_provider
    return get_provider()


def _tool_backup_run(args: dict) -> str:
    import json
    provider = _get_provider()
    if not provider:
        return json.dumps({"error": "No backup provider configured. Set HERMES_BACKUP_PROVIDER in .env"})
    return provider.run_backup(scope=args.get("scope", "full"))


def _tool_backup_list(args: dict) -> str:
    import json
    provider = _get_provider()
    if not provider:
        return json.dumps({"error": "No backup provider configured"})
    return provider.list_snapshots()


def _tool_backup_restore(args: dict) -> str:
    import json
    provider = _get_provider()
    if not provider:
        return json.dumps({"error": "No backup provider configured"})
    return provider.restore_snapshot(
        snapshot=args["snapshot"],
        scope=args.get("scope", "full"),
    )


def _tool_backup_status(args: dict) -> str:
    import json
    provider = _get_provider()
    if not provider:
        return json.dumps({"status": "not_configured", "message": "No backup provider configured"})
    return provider.status()