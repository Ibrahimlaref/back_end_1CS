from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
@patch("apps.core.api.v1.views.health.cache.get", return_value=None)
def test_health_returns_200_when_db_and_redis_are_up(_mock_cache_get):
    client = APIClient()

    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
    }


@pytest.mark.django_db
@patch("apps.core.api.v1.views.health.cache.get", return_value=None)
@patch("apps.core.api.v1.views.health.connection.cursor", side_effect=Exception("db down"))
def test_health_returns_503_when_db_is_unavailable(_mock_cursor, _mock_cache_get):
    client = APIClient()

    response = client.get("/health/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "db": "error",
        "redis": "ok",
    }


@pytest.mark.django_db
@patch("apps.core.api.v1.views.health.cache.get", side_effect=Exception("redis down"))
def test_health_returns_503_when_redis_is_unavailable(_mock_cache_get):
    client = APIClient()

    response = client.get("/health/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "db": "ok",
        "redis": "error",
    }
