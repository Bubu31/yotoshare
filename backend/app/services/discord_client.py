"""HTTP client for the discord-bot service. Replaces the embedded discord_bot module."""

import json
import logging
from typing import Optional, List

import httpx

logger = logging.getLogger(__name__)


def _settings():
    from app.config import get_settings
    return get_settings()


def _headers() -> dict:
    return {"X-Service-Key": _settings().service_api_key}


def _bot_url() -> str:
    return _settings().discord_bot_url


# ─── Called from async routes ──────────────────────────────────────────────

async def publish_archive(
    archive_id: int,
    title: str,
    author: str,
    description: str,
    cover_url: Optional[str] = None,
    file_size: int = 0,
    total_duration: Optional[int] = None,
    chapters_count: Optional[int] = None,
    chapters: Optional[List[dict]] = None,
    categories: Optional[List[str]] = None,
) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_bot_url()}/publish/archive",
            json={
                "archive_id": archive_id,
                "title": title,
                "author": author,
                "description": description,
                "cover_url": cover_url,
                "file_size": file_size,
                "total_duration": total_duration,
                "chapters_count": chapters_count,
                "chapters": chapters,
                "categories": categories,
            },
            headers=_headers(),
            timeout=40.0,
        )
        r.raise_for_status()
        return r.json()["thread_id"]


async def publish_pack(
    pack_id: int,
    name: str,
    description: str,
    image_url: Optional[str] = None,
    total_size: int = 0,
    archive_titles: Optional[List[str]] = None,
) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_bot_url()}/publish/pack",
            json={
                "pack_id": pack_id,
                "name": name,
                "description": description,
                "image_url": image_url,
                "total_size": total_size,
                "archive_titles": archive_titles or [],
            },
            headers=_headers(),
            timeout=40.0,
        )
        r.raise_for_status()
        return r.json()["thread_id"]


# ─── Called from sync code in archives.py ─────────────────────────────────

async def notify_new_submission(
    submission_id: int,
    title: str | None = None,
    pseudonym: str | None = None,
    chapters_count: int | None = None,
    file_size: int = 0,
    is_rework: bool = False,
) -> bool:
    url = _bot_url()
    if not url:
        logger.warning("DISCORD_BOT_URL not configured, skipping submission notification")
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{url}/notify/submission",
                json={
                    "submission_id": submission_id,
                    "title": title,
                    "pseudonym": pseudonym,
                    "chapters_count": chapters_count,
                    "file_size": file_size,
                    "is_rework": is_rework,
                },
                headers=_headers(),
                timeout=15.0,
            )
            return r.status_code == 200
    except Exception as e:
        logger.error("Failed to notify submission %d: %s", submission_id, e)
        return False


def delete_discord_thread(thread_id: str) -> bool:
    url = _bot_url()
    if not url:
        logger.warning("DISCORD_BOT_URL not configured, skipping thread delete")
        return False
    try:
        with httpx.Client() as client:
            r = client.delete(
                f"{url}/thread/{thread_id}",
                headers=_headers(),
                timeout=15.0,
            )
            return r.status_code == 200 and r.json().get("success", False)
    except Exception as e:
        logger.error("Failed to delete Discord thread %s: %s", thread_id, e)
        return False


def edit_discord_thread(
    thread_id: str,
    title: str,
    author: str,
    description: str,
    cover_url: Optional[str] = None,
    file_size: int = 0,
    total_duration: Optional[int] = None,
    chapters_count: Optional[int] = None,
    chapters: Optional[List[dict]] = None,
    categories: Optional[List[str]] = None,
    archive_id: Optional[int] = None,
) -> bool:
    url = _bot_url()
    if not url:
        logger.warning("DISCORD_BOT_URL not configured, skipping thread edit")
        return False
    try:
        with httpx.Client() as client:
            r = client.put(
                f"{url}/thread/{thread_id}",
                json={
                    "title": title,
                    "author": author,
                    "description": description,
                    "cover_url": cover_url,
                    "file_size": file_size,
                    "total_duration": total_duration,
                    "chapters_count": chapters_count,
                    "chapters": chapters,
                    "categories": categories,
                    "archive_id": archive_id,
                },
                headers=_headers(),
                timeout=20.0,
            )
            return r.status_code == 200 and r.json().get("success", False)
    except Exception as e:
        logger.error("Failed to edit Discord thread %s: %s", thread_id, e)
        return False


def create_forum_tag(tag_name: str, emoji: str = "🗄️") -> bool:
    url = _bot_url()
    if not url:
        return False
    try:
        with httpx.Client() as client:
            r = client.post(
                f"{url}/tag",
                json={"name": tag_name, "emoji": emoji},
                headers=_headers(),
                timeout=10.0,
            )
            return r.status_code == 200 and r.json().get("success", False)
    except Exception as e:
        logger.error("Failed to create Discord tag %s: %s", tag_name, e)
        return False


def delete_forum_tag(tag_name: str) -> bool:
    url = _bot_url()
    if not url:
        return False
    try:
        with httpx.Client() as client:
            r = client.delete(
                f"{url}/tag/{tag_name}",
                headers=_headers(),
                timeout=10.0,
            )
            return r.status_code == 200 and r.json().get("success", False)
    except Exception as e:
        logger.error("Failed to delete Discord tag %s: %s", tag_name, e)
        return False
