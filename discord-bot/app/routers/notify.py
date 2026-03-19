import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_service_key
from app.bot import _run_in_bot_loop, _do_notify_submission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notify"])


class NotifySubmissionRequest(BaseModel):
    submission_id: int
    title: Optional[str] = None
    pseudonym: Optional[str] = None
    chapters_count: Optional[int] = None
    file_size: int = 0
    is_rework: bool = False


@router.post("/notify/submission")
async def notify_submission(data: NotifySubmissionRequest, _=Depends(require_service_key)):
    try:
        _run_in_bot_loop(
            _do_notify_submission(
                submission_id=data.submission_id,
                title=data.title,
                pseudonym=data.pseudonym,
                chapters_count=data.chapters_count,
                file_size=data.file_size,
                is_rework=data.is_rework,
            ),
            timeout=15.0,
        )
        return {"success": True}
    except Exception as e:
        logger.error("notify_submission error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
