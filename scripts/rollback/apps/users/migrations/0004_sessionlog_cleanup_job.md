# Rollback Manifest: users 0004_sessionlog_cleanup_job

- Forward migration: `users.0004_sessionlog_cleanup_job`
- Rollback target: `users.0003_emailotpverification_purpose`

## Command
```bash
python manage.py migrate users 0003_emailotpverification_purpose
```

## Notes
- This rollback removes index `sessionlog_user_revoked_idx` and the seeded periodic task.
- Existing session rows remain unchanged.
