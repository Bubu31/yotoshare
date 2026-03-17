"""Tests that static routes are not shadowed by dynamic {id} routes.

This is the most critical test file — it guards against the exact class of bug
that caused 422 errors on /api/packs/assets and would cause similar issues on
/api/archives/cover/* if the route order regresses.
"""

import pytest
from httpx import AsyncClient


class TestPacksRouteOrdering:
    """Ensure /api/packs static routes are reachable (not shadowed by /{pack_id})."""

    @pytest.mark.asyncio
    async def test_assets_not_shadowed_by_pack_id(self, client: AsyncClient, admin_headers):
        """GET /api/packs/assets must NOT return 422 (would mean /{pack_id} captured 'assets')."""
        resp = await client.get("/api/packs/assets", headers=admin_headers)
        assert resp.status_code != 422, (
            "Route /assets is shadowed by /{pack_id} — move it BEFORE dynamic routes"
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_assets_returns_valid_json(self, client: AsyncClient, admin_headers):
        resp = await client.get("/api/packs/assets", headers=admin_headers)
        data = resp.json()
        assert "background" in data
        assert "mascot" in data

    @pytest.mark.asyncio
    async def test_assets_background_image_not_shadowed(self, client: AsyncClient):
        """GET /api/packs/assets/background/image must not 422."""
        resp = await client.get("/api/packs/assets/background/image")
        # 404 is fine (no asset uploaded), but NOT 422
        assert resp.status_code != 422

    @pytest.mark.asyncio
    async def test_signed_download_not_shadowed(self, client: AsyncClient):
        """GET /api/packs/signed-download/xxx must not 422."""
        resp = await client.get("/api/packs/signed-download/fake-token")
        assert resp.status_code != 422

    @pytest.mark.asyncio
    async def test_by_token_download_not_shadowed(self, client: AsyncClient):
        """GET /api/packs/by-token/xxx/download-all must not 422."""
        resp = await client.get("/api/packs/by-token/fake-token/download-all")
        assert resp.status_code != 422


class TestArchivesRouteOrdering:
    """Ensure /api/archives static routes are reachable."""

    @pytest.mark.asyncio
    async def test_cover_not_shadowed_by_archive_id(self, client: AsyncClient):
        """GET /api/archives/cover/test.jpg must NOT return 422."""
        resp = await client.get("/api/archives/cover/nonexistent.jpg")
        assert resp.status_code != 422, (
            "Route /cover/{filename} is shadowed by /{archive_id} — move it BEFORE dynamic routes"
        )
        # 404 is expected (file doesn't exist)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_grid_visual_not_shadowed(self, client: AsyncClient, admin_headers):
        """GET /api/archives/grid-visual must NOT return 422."""
        resp = await client.get("/api/archives/grid-visual", headers=admin_headers)
        assert resp.status_code != 422


class TestAllStaticRoutesReachable:
    """Smoke test: hit every static sub-path under routers with dynamic params."""

    PACKS_STATIC_PATHS = [
        "/api/packs/assets",
        "/api/packs/assets/background/image",
        "/api/packs/assets/mascot/image",
        "/api/packs/signed-download/test",
        "/api/packs/by-token/test/download-all",
    ]

    ARCHIVES_STATIC_PATHS = [
        "/api/archives/cover/test.jpg",
        "/api/archives/grid-visual",
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PACKS_STATIC_PATHS)
    async def test_packs_static_path_not_422(self, client: AsyncClient, admin_headers, path):
        resp = await client.get(path, headers=admin_headers)
        assert resp.status_code != 422, f"{path} returned 422 — route shadowed by dynamic param"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ARCHIVES_STATIC_PATHS)
    async def test_archives_static_path_not_422(self, client: AsyncClient, admin_headers, path):
        resp = await client.get(path, headers=admin_headers)
        assert resp.status_code != 422, f"{path} returned 422 — route shadowed by dynamic param"
