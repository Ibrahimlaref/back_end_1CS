# Rollback Manifest: core 0005_systemlog

- Forward migration: `core.0005_systemlog`
- Rollback target: `core.0004_request_log`

## Command
```bash
python manage.py migrate core 0004_request_log
```

## Notes
- This rollback drops table `system_logs`.
- Archive operational logs if needed.
