"""
Tool schemas for hermes-backup plugin.

Each schema is a JSON Schema dict that the LLM reads to decide when to
call a tool. Be descriptive — the agent relies on the 'description' field.
"""

BACKUP_NOW = {
    "name": "backup_now",
    "description": (
        "Create an immediate backup of Hermes agent data (config, state, "
        "skills, profiles, memory, and kanban database) to the configured "
        "cloud storage provider (S3 by default). Specify an optional scope "
        "to back up only a subset of data. Returns status and remote key."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "description": (
                    "Optional scope override: 'all' (default), 'config', "
                    "'state', 'skills', 'profiles', 'kanban', or a comma-"
                    "separated list like 'config,skills'."
                ),
                "default": "all",
            },
            "label": {
                "type": "string",
                "description": (
                    "Optional human-readable label for this backup "
                    "(e.g. 'before-migration', 'weekly-snapshot'). "
                    "Appended to the backup manifest."
                ),
            },
        },
        "required": [],
    },
}

BACKUP_STATUS = {
    "name": "backup_status",
    "description": (
        "Show backup configuration status: which provider is active, "
        "whether it is connected, what scopes are configured, and when "
        "the last backup was taken."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "detailed": {
                "type": "boolean",
                "description": "If true, show full provider connection details.",
            },
        },
        "required": [],
    },
}

BACKUP_LIST = {
    "name": "backup_list",
    "description": (
        "List recent backups stored on the configured remote provider. "
        "Returns a table of keys, sizes, and timestamps. Use the key "
        "from this list to restore a specific backup."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max number of backups to list (default: 10).",
                "default": 10,
            },
            "prefix": {
                "type": "string",
                "description": "Optional prefix filter (e.g. 'skills/' or 'config.yaml').",
            },
        },
        "required": [],
    },
}

BACKUP_RESTORE = {
    "name": "backup_restore",
    "description": (
        "Restore Hermes agent data from a previous backup. Specify a "
        "backup key (from backup_list) or a scope to restore the most "
        "recent backup of that scope. DANGER: this overwrites current files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": (
                    "Specific backup key to restore (from backup_list). "
                    "If omitted, restores the latest backup across all scopes."
                ),
            },
            "scope": {
                "type": "string",
                "description": (
                    "Scope filter for restore: 'all', 'config', 'state', "
                    "'skills', 'profiles', 'kanban'. Only restores matching "
                    "files from the backup archive."
                ),
                "default": "all",
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, show what would be restored without writing anything.",
                "default": False,
            },
        },
        "required": [],
    },
}