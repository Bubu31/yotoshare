import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_service_key
from app.bot import _do_create_forum_tag, _do_delete_forum_tag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tag", tags=["tag"])


class CreateTagRequest(BaseModel):
    name: str
    emoji: str = "🗄️"


@router.post("")
async def create_tag(data: CreateTagRequest, _=Depends(require_service_key)):
    try:
        ok = await _do_create_forum_tag(data.name, data.emoji)
        return {"success": ok}
    except Exception as e:
        logger.error("create_tag error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.delete("/{tag_name}")
async def delete_tag(tag_name: str, _=Depends(require_service_key)):
    try:
        ok = await _do_delete_forum_tag(tag_name)
        return {"success": ok}
    except Exception as e:
        logger.error("delete_tag error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
