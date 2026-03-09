import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import aiofiles

logger = logging.getLogger(__name__)
from app.database import get_db
from app.models import Archive, DownloadToken
from app.schemas import DownloadTokenCreate, DownloadTokenResponse
from app.services import storage, token as token_service
from app.auth import get_current_user, require_permission
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/download", tags=["download"])


@router.post("/token", response_model=DownloadTokenResponse)
async def create_download_token(
    data: DownloadTokenCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "access")),
):
    archive = db.query(Archive).filter(Archive.id == data.archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    token, expires_at = token_service.create_download_token(
        db, data.archive_id, data.discord_user_id, data.expiry_seconds, data.reusable
    )

    return DownloadTokenResponse(
        token=token,
        expires_at=expires_at,
        download_url=token_service.get_download_url(token),
    )


@router.get("/{token}")
async def download_file(token: str, db: Session = Depends(get_db)):
    archive = token_service.validate_token(db, token)
    if not archive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired download link"
        )

    # Mark token as used only for single-use tokens
    db_token = db.query(DownloadToken).filter(DownloadToken.token == token).first()
    if not db_token.reusable:
        token_service.mark_token_used(db, token)

    # Increment download counter
    archive.download_count = (archive.download_count or 0) + 1
    db.commit()

    filepath = storage.get_archive_path(archive.archive_path)
    if not filepath:
        logger.warning("Archive file not found: %s", archive.archive_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archive file not found: {archive.archive_path}"
        )

    async def file_iterator():
        try:
            async with aiofiles.open(filepath, "rb") as f:
                while chunk := await f.read(1024 * 1024):
                    yield chunk
        except Exception as e:
            logger.error("Error reading file: %s", e)
            raise

    safe_title = "".join(c for c in archive.title if c.isalnum() or c in " -_").strip()
    filename = f"{safe_title}.zip"

    return StreamingResponse(
        file_iterator(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(archive.file_size),
        },
    )


@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_tokens(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    count = token_service.cleanup_expired_tokens(db)
    return {"deleted": count}
