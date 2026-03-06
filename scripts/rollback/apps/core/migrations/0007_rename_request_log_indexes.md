# Rollback Manifest: core 0007_rename_request_log_indexes

- Forward migration: `core.0007_rename_request_log_indexes`
- Rollback target: `core.0006_dbschemaversion`

## Command
```bash
python manage.py migrate core 0006_dbschemaversion
```

## Notes
- This rollback restores previous request log index names.
