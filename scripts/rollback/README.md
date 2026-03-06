# Rollback Manifests

For each new migration file, add a rollback manifest at:

`scripts/rollback/<app>/migrations/<migration_name>.md`

## Required content
- Forward migration identifier
- Target rollback migration
- Exact rollback command
- Data safety notes
- Post-rollback verification query/check
