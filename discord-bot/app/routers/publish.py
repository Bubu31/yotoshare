import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_service_key
from app.bot import _run_in_bot_loop, _do_publish, _do_publish_pack

logger = logging.getLogger(__name__)
router = APIRouter(tags=["publish"])


class PublishArchiveRequest(BaseModel):
    archive_id: int
    title: str
    author: str
    description: str
    cover_url: Optional[str] = None
    file_size: int = 0
    total_duration: Optional[int] = None
    chapters_count: Optional[int] = None
    chapters: Optional[List[dict]] = None
    categories: Optional[List[str]] = None


class PublishPackRequest(BaseModel):
    pack_id: int
    name: str
    description: str
    image_url: Optional[str] = None
    total_size: int = 0
    archive_titles: List[str] = []


class PublishResponse(BaseModel):
    success: bool
    thread_id: Optional[str] = None
    message: str = ""


@router.post("/publish/archive", response_model=PublishResponse)
async def publish_archive(data: PublishArchiveRequest, _=Depends(require_service_key)):
    try:
        thread_id = _run_in_bot_loop(
            _do_publish(
                archive_id=data.archive_id,
                title=data.title,
                author=data.author,
                description=data.description,
                cover_url=data.cover_url,
                file_size=data.file_size,
                total_duration=data.total_duration,
                chapters_count=data.chapters_count,
                chapters=data.chapters,
                categories=data.categories,
            ),
            timeout=35.0,
        )
        return PublishResponse(success=True, thread_id=thread_id)
    except Exception as e:
        logger.error("publish_archive error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/publish/pack", response_model=PublishResponse)
async def publish_pack(data: PublishPackRequest, _=Depends(require_service_key)):
    try:
        thread_id = _run_in_bot_loop(
            _do_publish_pack(
                pack_id=data.pack_id,
                name=data.name,
                description=data.description,
                image_url=data.image_url,
                total_size=data.total_size,
                archive_titles=data.archive_titles,
            ),
            timeout=35.0,
        )
        return PublishResponse(success=True, thread_id=thread_id)
    except Exception as e:
        logger.error("publish_pack error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
