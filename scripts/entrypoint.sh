#!/bin/bash
set -e

echo "Waiting for database..."
python manage.py wait_for_db

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running migrations..."
    python manage.py migrate
fi

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

if [ "${LOAD_DEV_FIXTURES:-false}" = "true" ] && [ -f "fixtures/dev_seed.json" ]; then
    echo "Loading development fixtures..."
    python manage.py loaddata fixtures/dev_seed.json
fi

echo "Ready - starting server..."
exec "$@"
