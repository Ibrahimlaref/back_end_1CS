# brahim

## API Request Logging and Tracing

### What is logged
- Every `/api/*` request is timed by `RequestLoggingMiddleware`.
- `RequestLog` stores: `method`, `path`, `status_code`, `duration_ms`, `gym_id`, `user_id`, `timestamp`, `is_slow`.
- `is_slow` is set when `duration_ms > REQUEST_LOG_SLOW_MS` (default `1000ms`).

### Sampling policy
- Errors (`status_code >= 400`) are always persisted/logged.
- Success responses (`2xx`) are sampled by `REQUEST_LOG_SUCCESS_SAMPLE_RATE` (default `0.10`).
- Metrics collection runs for all API requests, even if persistence is skipped by sampling.

### Redis latency metrics + P95 alerting
- Redis rolling buffers are updated with `LPUSH + LTRIM + EXPIRE`.
- Buffers are maintained globally and per route.
- Global P95 is computed every request.
- If global P95 exceeds `REQUEST_LOG_P95_ALERT_MS` (default `500ms`), an alert event is emitted.
- Alert spam is prevented with Redis cooldown key `SET NX EX` using `REQUEST_LOG_ALERT_COOLDOWN_SEC` (default `300s`).

### Structured JSON logs (ELK/Loki/DataDog ready)
- Request events are emitted as one-line JSON logs (`event=api_request`).
- Alert events are emitted as one-line JSON logs (`event=latency_alert`).
- Key fields include: `event`, `trace_id`, `request_id`, `method`, `path`, `status_code`, `duration_ms`, `is_slow`, `gym_id`, `user_id`, `timestamp`, `sampled`, `p95_ms`, `alert_type`.

### Sentry integration
- Set `SENTRY_DSN` to enable Sentry initialization.
- If `SENTRY_DSN` is empty, Sentry is disabled.
- `SENTRY_TRACES_SAMPLE_RATE` controls tracing sample rate (default `0.10`).

### Configuration
- `REQUEST_LOGGING_ENABLED` (default `True`)
- `REQUEST_LOG_SUCCESS_SAMPLE_RATE` (default `0.10`)
- `REQUEST_LOG_SLOW_MS` (default `1000`)
- `REQUEST_LOG_P95_ALERT_MS` (default `500`)
- `REQUEST_LOG_BUFFER_SIZE` (default `1000`)
- `REQUEST_LOG_BUFFER_TTL_SEC` (default `900`)
- `REQUEST_LOG_ALERT_COOLDOWN_SEC` (default `300`)
- `OBSERVABILITY_PROVIDER` (default `stdout`)
- `SENTRY_DSN` (default empty)
- `SENTRY_TRACES_SAMPLE_RATE` (default `0.10`)

## CI/CD Pipeline (GitHub Actions)

### Pull Request CI
- Workflow file: `.github/workflows/ci.yml`
- Trigger: every PR to `main`
- Runs:
  - `flake8` lint
  - `mypy` type checks
  - `pytest` with coverage gate (`>=80%`)
  - `bandit` security scan
  - Migration checks:
    - `python manage.py makemigrations --check --dry-run`
    - `python manage.py lintmigrations --warnings-as-errors`

### Docker publish
- Workflow file: `.github/workflows/docker-publish.yml`
- Trigger: pushes to `main`
- Builds and pushes image to GHCR:
  - `ghcr.io/<owner>/<repo>:latest`
  - `ghcr.io/<owner>/<repo>:<sha>`

### Required GitHub repo setting (manual)
- Enable branch protection for `main`.
- Mark CI status checks as required before merge.

## Database Migration Strategy

### Zero-downtime + reversibility
- Governance rules: `docs/migrations/zero_downtime.md`
- Rehearsal reports: `docs/migrations/reports/`
- Rollback manifests: `scripts/rollback/`

### CI migration governance checks
- `python manage.py makemigrations --check --dry-run`
- `python manage.py lintmigrations --warnings-as-errors`
- `python scripts/check_migration_governance.py --base-ref <base-branch>`
- `python scripts/check_migration_squash_policy.py --max-per-app 50`

### Schema version tracking
- Table: `db_schema_versions`
- Command:
  - `python manage.py track_schema_version --environment=<env> --git-sha=<sha> --version-label=<label>`

## Production Environment Configuration

### What is enforced
- Production settings module: `brahim.settings.prod`
- `DEBUG=False` is hard-enforced in production settings.
- `SECRET_KEY`, `JWT_SECRET_KEY`, and `STRIPE_SECRET_KEY` are required from environment variables.
- `CORS_ORIGIN_ALLOW_ALL=False` in production; `CORS_ALLOWED_ORIGINS` must be provided.
- `ALLOWED_HOSTS` must be provided.
- PgBouncer mode can be enabled with `PGBOUNCER_ENABLED=True` and `DB_CONN_MAX_AGE=0` (default in prod).

### Secret handling contract
- Do not store secrets in repository files.
- Do not pass secrets as Docker build args.
- Inject runtime secrets from a vault/secret manager into container environment variables.
- `.dockerignore` excludes `.env*` so local env files are not baked into images.

### Files added for setup
- `.env.example` for local development defaults.
- `.env.prod.example` for production variable names/placeholders only.
- `docker-compose.prod.yml` includes a `pgbouncer` service and routes Django/Celery DB traffic through it.
