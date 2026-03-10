# Rollback Manifest: membersNsubscription 0001_initial

- Forward migration: `membersNsubscription.0001_initial`
- Rollback target: `membersNsubscription.zero`

## Command
```bash
python manage.py migrate membersNsubscription zero
```

## Notes
- This rollback drops all tables introduced by the `membersNsubscription` app.
- Any data created in memberships, reservations, payments, products, rooms, messaging, and analytics tables will be lost unless exported first.
- Run this only when the application code no longer depends on the app being installed.

## Verification
```sql
SELECT to_regclass('membersNsubscription_gym');
```

- Expect `NULL` after rollback.
