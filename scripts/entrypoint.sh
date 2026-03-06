#!/bin/bash
set -e

echo "⏳ Waiting for database..."
python manage.py wait_for_db

echo "📦 Running migrations..."
python manage.py migrate

echo "🌱 Loading fixtures..."
if [ -f "fixtures/dev_seed.json" ]; then
    python manage.py loaddata fixtures/dev_seed.json
fi

echo "✅ Ready — starting server..."
exec "$@"