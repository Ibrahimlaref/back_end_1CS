# Waiver: users 0005_user_retention_fields

## Why the risky operation is required
- The retention policy needs `is_deleted` and `is_anonymised` to be immediately usable as boolean flags in auth, retention, and admin code paths.
- Allowing `NULL` here would introduce a third state that the current application logic does not model.

## Mitigation steps
- The new booleans are added with a constant default of `false`, which PostgreSQL 16 applies without rewriting the whole table.
- Rollback is documented in `scripts/rollback/apps/users/migrations/0005_user_retention_fields.md`.
- Existing rows default to the safe inactive state until the retention job updates them.

## Rollback impact
- Rollback removes the retention markers from `users`.
- Export any compliance state based on these columns before reverting.

## Approval owner
- Backend platform maintainer for the compliance rollout.
