"""
hermes-backup — Multi-Storage Backup Plugin for Hermes Agent.

Registers 4 tools (backup_now, backup_status, backup_list, backup_restore),
a CLI command (hermes backup <subcommand>), an on_session_end hook, and
a /backup slash command.

Usage:
  /backup now                    — immediate backup
  /backup status                 — show provider/connection status
  /backup list                   — list remote backups
  /backup restore --key <key>    — restore from a backup
  hermes backup now --scope config,skills
"""

import json
import shlex

from . import schemas
from . import tools as handlers
from . import config as plugin_config


def register(ctx):
    """Called once at startup — wire up tools, hooks, CLI, and slash commands."""

    # ── Register 4 backup tools ─────────────────────────────────────
    ctx.register_tool(
        name="backup_now",
        toolset="hermes-backup",
        schema=schemas.BACKUP_NOW,
        handler=handlers.backup_now,
        description="Create an immediate backup of Hermes agent data to cloud storage.",
    )

    ctx.register_tool(
        name="backup_status",
        toolset="hermes-backup",
        schema=schemas.BACKUP_STATUS,
        handler=handlers.backup_status,
        description="Show backup provider status and configuration.",
    )

    ctx.register_tool(
        name="backup_list",
        toolset="hermes-backup",
        schema=schemas.BACKUP_LIST,
        handler=handlers.backup_list,
        description="List recent backups stored on the remote provider.",
    )

    ctx.register_tool(
        name="backup_restore",
        toolset="hermes-backup",
        schema=schemas.BACKUP_RESTORE,
        handler=handlers.backup_restore,
        description="Restore Hermes agent data from a previous backup.",
    )

    # ── Hook: auto-backup on session end ────────────────────────────
    if plugin_config.load().get("auto_backup", False):
        ctx.register_hook("on_session_end", handlers.on_session_end_hook)

    # ── CLI command: hermes backup <subcommand> ─────────────────────
    ctx.register_cli_command(
        name="backup",
        help="Backup Hermes agent data: now, status, list, restore",
        setup_fn=lambda: None,
        handler_fn=lambda args: handlers.cli_backup(args),
    )

    # ── Slash command: /backup ──────────────────────────────────────
    def cmd_backup(raw_args: str, **kwargs) -> str:
        args = shlex.split(raw_args) if raw_args else []
        return handlers.cli_backup(args)

    ctx.register_command(
        name="backup",
        description="Backup Hermes agent data: now, status, list, restore [options]",
        handler=cmd_backup,
    )