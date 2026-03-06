# Migration Rehearsal Reports

Each PR that introduces new migrations must add at least one report file in this directory.

## Minimum report content
- PR / branch reference
- Dataset scale (rows per impacted table)
- Migration execution duration
- Observed locks / contention
- Rollback execution result
- Final verification queries and output summary

Use date-based filenames, for example:
- `2026-03-06_core-schema-rehearsal.md`
