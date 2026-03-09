#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
IMAGE_TAG="${IMAGE_TAG:?Set IMAGE_TAG}"
DJANGO_REPLICAS="${DJANGO_REPLICAS:-3}"
HEALTH_URL="${HEALTH_URL:-http://localhost/health}"
FAILED=0

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

echo "Pulling image: $IMAGE_TAG"
docker pull "$IMAGE_TAG"

echo "Running migrations"
if ! compose run --rm django python manage.py migrate --noinput; then
  echo "Migration step failed"
  exit 1
fi

for worker in $(seq 1 "$DJANGO_REPLICAS"); do
  service="django_${worker}"
  echo "Updating ${service}"

  if ! compose up -d --no-deps "$service"; then
    echo "Failed to update ${service}"
    FAILED=1
    break
  fi

  if ! curl --retry 10 --retry-delay 3 --fail "$HEALTH_URL" >/dev/null; then
    echo "Health check failed after updating ${service}"
    FAILED=1
    break
  fi
done

if [ "$FAILED" -eq 0 ]; then
  echo "Rolling deploy succeeded for ${DJANGO_REPLICAS} Django workers."
else
  echo "Rolling deploy failed."
  exit 1
fi
