"""Tests for archives CRUD operations."""

import pytest
from httpx import AsyncClient


class TestGetArchive:
    """GET /api/archives/{id}."""

    @pytest.mark.asyncio
    async def test_get_existing_archive(self, client: AsyncClient, sample_archives):
        archive = sample_archives[0]
        resp = await client.get(f"/api/archives/{archive.id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == archive.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_archive(self, client: AsyncClient):
        resp = await client.get("/api/archives/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_archive_invalid_id(self, client: AsyncClient):
        """Non-integer ID should return 422, not 500."""
        resp = await client.get("/api/archives/not-a-number")
        assert resp.status_code == 422


class TestDeleteArchive:
    """DELETE /api/archives/{id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient, sample_archives):
        resp = await client.delete(f"/api/archives/{sample_archives[0].id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient, admin_headers):
        resp = await client.delete("/api/archives/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestArchiveListResponse:
    """Verify the list response structure."""

    @pytest.mark.asyncio
    async def test_list_item_has_required_fields(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"limit": 1})
        data = resp.json()
        item = data["items"][0]
        required = ["id", "title", "created_at"]
        for field in required:
            assert field in item, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get("/api/archives")
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
