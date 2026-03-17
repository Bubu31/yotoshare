"""Tests for authentication and authorization."""

import pytest
from httpx import AsyncClient


class TestAuthRequired:
    """Endpoints that require auth should return 401 without token."""

    PROTECTED_ENDPOINTS = [
        ("POST", "/api/archives"),
        ("GET", "/api/packs"),
        ("POST", "/api/packs"),
        ("GET", "/api/packs/assets"),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    async def test_no_token_returns_401(self, client: AsyncClient, method, path):
        resp = await client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should require auth"


class TestPublicEndpoints:
    """Endpoints that should be accessible without auth."""

    @pytest.mark.asyncio
    async def test_archives_list_is_public(self, client: AsyncClient):
        resp = await client.get("/api/archives")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_is_public(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code in (200, 503)  # 503 if DB not fully initialized

    @pytest.mark.asyncio
    async def test_cover_is_public(self, client: AsyncClient):
        resp = await client.get("/api/archives/cover/anything.jpg")
        # 404 OK (no file), but must not be 401
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_pack_image_is_public(self, client: AsyncClient):
        resp = await client.get("/api/packs/1/image")
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_asset_image_is_public(self, client: AsyncClient):
        resp = await client.get("/api/packs/assets/background/image")
        assert resp.status_code != 401


class TestPermissions:
    """Role-based access control."""

    @pytest.mark.asyncio
    async def test_admin_can_access_packs(self, client: AsyncClient, admin_headers):
        resp = await client.get("/api/packs", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_editor_can_access_packs(self, client: AsyncClient, editor_headers):
        resp = await client.get("/api/packs", headers=editor_headers)
        assert resp.status_code == 200
