"""Tests for packs CRUD operations."""

import pytest
from httpx import AsyncClient


class TestGetPack:
    """GET /api/packs/{id}."""

    @pytest.mark.asyncio
    async def test_get_existing_pack(self, client: AsyncClient, admin_headers, sample_packs):
        pack = sample_packs[0]
        resp = await client.get(f"/api/packs/{pack.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == pack.name
        assert "archives" in data
        assert "share_url" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_pack(self, client: AsyncClient, admin_headers):
        resp = await client.get("/api/packs/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestCreatePack:
    """POST /api/packs."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/packs", json={
            "name": "Test Pack",
            "archive_ids": [1],
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_empty_archives_rejected(self, client: AsyncClient, admin_headers):
        resp = await client.post("/api/packs", json={
            "name": "Test Pack",
            "archive_ids": [],
        }, headers=admin_headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_nonexistent_archives_rejected(self, client: AsyncClient, admin_headers):
        resp = await client.post("/api/packs", json={
            "name": "Test Pack",
            "archive_ids": [99999],
        }, headers=admin_headers)
        assert resp.status_code == 404


class TestPackResponse:
    """Verify pack response structure."""

    @pytest.mark.asyncio
    async def test_pack_has_required_fields(self, client: AsyncClient, admin_headers, sample_packs):
        resp = await client.get(f"/api/packs/{sample_packs[0].id}", headers=admin_headers)
        data = resp.json()
        required = ["id", "name", "token", "expires_at", "archive_count", "archives", "share_url", "created_at"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_pack_archive_info_fields(self, client: AsyncClient, admin_headers, sample_packs):
        resp = await client.get(f"/api/packs/{sample_packs[1].id}", headers=admin_headers)
        data = resp.json()
        if data["archives"]:
            archive = data["archives"][0]
            for field in ["id", "title", "author", "cover_path", "file_size"]:
                assert field in archive, f"Missing archive field: {field}"
