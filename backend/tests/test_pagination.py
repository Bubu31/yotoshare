"""Tests for pagination on archives and packs list endpoints."""

import pytest
from httpx import AsyncClient


class TestArchivesPagination:
    """GET /api/archives pagination."""

    @pytest.mark.asyncio
    async def test_returns_items_and_total(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data, "Response must have 'items' key"
        assert "total" in data, "Response must have 'total' key"

    @pytest.mark.asyncio
    async def test_default_limit_is_10(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives")
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25

    @pytest.mark.asyncio
    async def test_custom_limit(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"limit": 5})
        data = resp.json()
        assert len(data["items"]) == 5
        assert data["total"] == 25

    @pytest.mark.asyncio
    async def test_offset(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"limit": 10, "offset": 20})
        data = resp.json()
        assert len(data["items"]) == 5  # 25 total, offset 20 → 5 remaining
        assert data["total"] == 25

    @pytest.mark.asyncio
    async def test_offset_beyond_total(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"offset": 100})
        data = resp.json()
        assert len(data["items"]) == 0
        assert data["total"] == 25

    @pytest.mark.asyncio
    async def test_sort_alpha_asc(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"sort": "alpha-asc", "limit": 3})
        data = resp.json()
        titles = [a["title"] for a in data["items"]]
        assert titles == sorted(titles)

    @pytest.mark.asyncio
    async def test_sort_alpha_desc(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"sort": "alpha-desc", "limit": 3})
        data = resp.json()
        titles = [a["title"] for a in data["items"]]
        assert titles == sorted(titles, reverse=True)

    @pytest.mark.asyncio
    async def test_sort_downloads_desc(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"sort": "downloads-desc", "limit": 3})
        data = resp.json()
        counts = [a["download_count"] for a in data["items"]]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    async def test_search_filter(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"search": "Archive 00"})
        data = resp.json()
        for item in data["items"]:
            assert "Archive 00" in item["title"]

    @pytest.mark.asyncio
    async def test_hide_published(self, client: AsyncClient, sample_archives):
        resp = await client.get("/api/archives", params={"hide_published": True, "limit": 100})
        data = resp.json()
        for item in data["items"]:
            assert item["discord_post_id"] is None

    @pytest.mark.asyncio
    async def test_hide_published_changes_total(self, client: AsyncClient, sample_archives):
        all_resp = await client.get("/api/archives", params={"limit": 100})
        pub_resp = await client.get("/api/archives", params={"hide_published": True, "limit": 100})
        assert pub_resp.json()["total"] < all_resp.json()["total"]

    @pytest.mark.asyncio
    async def test_category_filter(self, client: AsyncClient, sample_archives, sample_categories, db):
        # Assign first archive to first category
        archive = sample_archives[0]
        archive.categories.append(sample_categories[0])
        db.commit()

        resp = await client.get("/api/archives", params={"category_id": sample_categories[0].id})
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_pagination_consistency(self, client: AsyncClient, sample_archives):
        """All pages combined should yield exactly total items with no duplicates."""
        all_ids = []
        offset = 0
        while True:
            resp = await client.get("/api/archives", params={"limit": 7, "offset": offset})
            data = resp.json()
            if not data["items"]:
                break
            all_ids.extend(a["id"] for a in data["items"])
            offset += 7

        assert len(all_ids) == 25
        assert len(set(all_ids)) == 25, "Duplicate items across pages"


class TestPacksPagination:
    """GET /api/packs pagination."""

    @pytest.mark.asyncio
    async def test_returns_items_and_total(self, client: AsyncClient, admin_headers, sample_packs):
        resp = await client.get("/api/packs", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_default_limit_is_10(self, client: AsyncClient, admin_headers, sample_packs):
        resp = await client.get("/api/packs", headers=admin_headers)
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15

    @pytest.mark.asyncio
    async def test_offset(self, client: AsyncClient, admin_headers, sample_packs):
        resp = await client.get("/api/packs", headers=admin_headers, params={"offset": 10})
        data = resp.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15

    @pytest.mark.asyncio
    async def test_pagination_consistency(self, client: AsyncClient, admin_headers, sample_packs):
        """All pages combined should yield exactly total items with no duplicates."""
        all_ids = []
        offset = 0
        while True:
            resp = await client.get("/api/packs", headers=admin_headers, params={"limit": 4, "offset": offset})
            data = resp.json()
            if not data["items"]:
                break
            all_ids.extend(p["id"] for p in data["items"])
            offset += 4

        assert len(all_ids) == 15
        assert len(set(all_ids)) == 15, "Duplicate items across pages"
