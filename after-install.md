# Hermes Backup Plugin — After Install

## 1. Install dependencies
```bash
cd ~/.hermes/plugins/hermes-backup
pip install -r requirements.txt
```

## 2. Configure environment
Add to `~/.hermes/.env`:
```bash
HERMES_BACKUP_PROVIDER=s3
HERMES_S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

## 3. Enable the plugin
```bash
hermes plugins enable hermes-backup
```

## 4. Test it
```bash
hermes backup now
hermes backup status
hermes backup list
```

For auto-backup on session end:
```bash
echo 'HERMES_BACKUP_AUTO=true' >> ~/.hermes/.env
```