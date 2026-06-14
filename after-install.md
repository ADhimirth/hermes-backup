# hermes-backup — After Install

## Setup

1. **Enable the plugin:**
   ```
   hermes plugins enable hermes-backup
   ```

2. **Set environment variables:**
   At minimum, S3 needs:
   ```
   export HERMES_BACKUP_S3_BUCKET=my-hermes-backups
   export AWS_ACCESS_KEY_ID=AKIA...
   export AWS_SECRET_ACCESS_KEY=...
   export AWS_DEFAULT_REGION=us-east-1
   ```

   Or set these in your `~/.hermes/.env` file.

3. **Install optional dependencies:**
   ```
   pip install boto3
   ```

4. **Verify:**
   ```
   hermes backup status
   ```

## Usage

| Command | What it does |
|---------|-------------|
| `/backup now` | Backup everything now |
| `/backup now --scope config,skills` | Backup only config + skills |
| `/backup now --label pre-migration` | Labeled backup |
| `/backup status` | Check provider connection |
| `/backup list` | List recent backups |
| `/backup list --prefix skills/` | Filter backups by prefix |
| `/backup restore --key <key>` | Restore from specific backup |
| `/backup restore --dry-run` | Preview what would restore |

CLI equivalents: `hermes backup now`, `hermes backup status`, etc.

## Auto-Backup

To auto-backup config on every session end:
```yaml
# ~/.hermes/plugins/hermes-backup/config.yaml
auto_backup: true
auto_backup_scope: config
```

## Adding a New Provider

1. Create `providers/myprovider.py` with a class inheriting `BaseBackupProvider`
2. Add a factory branch in `providers/__init__.py::load_provider()`
3. The new provider is available as `HERMES_BACKUP_PROVIDER=myprovider`