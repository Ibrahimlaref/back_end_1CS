# Migration Squashing Policy

## Objective
Keep migration history efficient so new environment bootstraps and deploy-time planning stay fast.

## Rule
- Soft threshold: max 50 migration files per app.
- CI fails when an app exceeds this threshold.

## When to squash
- At the end of a sprint/release cycle once all environments are on the same migration head.
- Prefer squashing old, stable migrations (not actively changing).

## Procedure
1. Verify all environments are fully migrated to current head.
2. Run Django squash for target range.
3. Validate:
- fresh database bootstrap,
- upgrade from previous released state,
- rollback path documentation updated.
4. Keep compatibility window (old + squashed paths) for one release where needed.
