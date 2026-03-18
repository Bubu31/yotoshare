import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_service_key
from app.bot import _run_in_bot_loop, _do_delete_thread, _do_edit_thread

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/thread", tags=["thread"])


class EditThreadRequest(BaseModel):
    title: str
    author: str
    description: str
    cover_url: Optional[str] = None
    file_size: int = 0
    total_duration: Optional[int] = None
    chapters_count: Optional[int] = None
    chapters: Optional[List[dict]] = None
    categories: Optional[List[str]] = None
    archive_id: Optional[int] = None


@router.delete("/{thread_id}")
async def delete_thread(thread_id: str, _=Depends(require_service_key)):
    try:
        ok = _run_in_bot_loop(_do_delete_thread(thread_id), timeout=15.0)
        return {"success": ok}
    except Exception as e:
        logger.error("delete_thread error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.put("/{thread_id}")
async def edit_thread(thread_id: str, data: EditThreadRequest, _=Depends(require_service_key)):
    try:
        ok = _run_in_bot_loop(
            _do_edit_thread(
                thread_id=thread_id,
                title=data.title,
                author=data.author,
                description=data.description,
                cover_url=data.cover_url,
                file_size=data.file_size,
                total_duration=data.total_duration,
                chapters_count=data.chapters_count,
                chapters=data.chapters,
                categories=data.categories,
                archive_id=data.archive_id,
            ),
            timeout=20.0,
        )
        return {"success": ok}
    except Exception as e:
        logger.error("edit_thread error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
