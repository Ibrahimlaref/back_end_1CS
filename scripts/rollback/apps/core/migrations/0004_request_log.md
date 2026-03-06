# Rollback Manifest: core 0004_request_log

- Forward migration: `core.0004_request_log`
- Rollback target: `core.0003_enable_rls`

## Command
```bash
python manage.py migrate core 0003_enable_rls
```

## Notes
- This rollback drops table `request_logs`.
- Export data if retention is required before rollback.
