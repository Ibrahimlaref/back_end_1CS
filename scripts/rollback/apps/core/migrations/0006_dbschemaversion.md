# Rollback Manifest: core 0006_dbschemaversion

- Forward migration: `core.0006_dbschemaversion`
- Rollback target: `core.0005_systemlog`

## Command
```bash
python manage.py migrate core 0005_systemlog
```

## Notes
- This rollback drops table `db_schema_versions`.
- Export schema tracking records first if required for audit.
