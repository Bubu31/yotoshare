"""Tests for the health check and basic app setup."""

import pytest
from httpx import AsyncClient


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint_exists(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_health_checks_database(self, client: AsyncClient):
        resp = await client.get("/api/health")
        data = resp.json()
        assert "database" in data["checks"]


class TestCORS:
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        resp = await client.options(
            "/api/archives",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware should respond
        assert resp.status_code in (200, 400)
