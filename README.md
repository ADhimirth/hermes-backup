# hermes-backup

Multi-storage backup plugin for [Hermes Agent](https://hermes-agent.nousresearch.com). Backs up config, state, skills, and profiles to S3, Google Drive, Dropbox, or any pluggable provider.

## Quick Start

```bash
# Install as a user plugin
git clone https://github.com/ADhimirth/hermes-backup.git ~/.hermes/plugins/hermes-backup

# Install dependencies
cd ~/.hermes/plugins/hermes-backup
pip install -r requirements.txt

# Configure
echo 'HERMES_BACKUP_PROVIDER=s3' >> ~/.hermes/.env
echo 'HERMES_S3_BUCKET=my-backup-bucket' >> ~/.hermes/.env
echo 'AWS_ACCESS_KEY_ID=xxx' >> ~/.hermes/.env
echo 'AWS_SECRET_ACCESS_KEY=xxx' >> ~/.hermes/.env

# Enable the plugin
hermes plugins enable hermes-backup

# Run a backup
hermes backup now
```

## Usage

| Command | Description |
|---------|-------------|
| `hermes backup now` | Run a full backup now |
| `hermes backup list` | List available snapshots |
| `hermes backup restore <snapshot>` | Restore from snapshot |
| `hermes backup status` | Check backup status |

In-session slash commands: `/backup now`, `/backup list`, `/backup restore`, `/backup status`

## Architecture

```
plugin.yaml              — Manifest
__init__.py              — register(): tools, hooks, commands
providers/
  __init__.py             — BaseBackupProvider interface + registry
  s3.py                   — AWS S3 provider (built-in)
config.yaml              — Default config
requirements.txt         — Python dependencies
```

## Providers

Built-in:
- **s3** — Amazon S3 (requires `boto3` + AWS credentials)

Roadmap:
- Google Drive
- Dropbox
- Local filesystem archive

## Development

```bash
git clone https://github.com/ADhimirth/hermes-backup.git
cd hermes-backup
pip install -r requirements.txt
# Hack away
```