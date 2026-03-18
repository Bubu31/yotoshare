"""Service endpoints for inter-service communication (discord-bot → yotoshare)."""

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Archive, Pack
from app.services.token import create_download_token, get_download_url, create_pack_signed_url

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/service", tags=["service"])


class ArchiveDownloadRequest(BaseModel):
    archive_id: int
    discord_user_id: str


class PackDownloadRequest(BaseModel):
    pack_id: int


@router.post("/download")
async def get_archive_download(
    data: ArchiveDownloadRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Called by discord-bot when a user clicks a download button. Returns embed data + download URL."""
    archive = db.query(Archive).filter(Archive.id == data.archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    token, _ = create_download_token(db, data.archive_id, data.discord_user_id, reusable=True)
    download_url = get_download_url(token)

    cover_url = None
    if archive.cover_path:
        cover_url = f"{settings.base_url}/api/archives/cover/{archive.cover_path}"

    return {
        "title": archive.title,
        "description": archive.description or "",
        "cover_url": cover_url,
        "download_url": download_url,
    }


@router.post("/pack-download")
async def get_pack_download(
    data: PackDownloadRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Called by discord-bot when a user clicks a pack download button. Returns embed data + download URL."""
    pack = db.query(Pack).filter(Pack.id == data.pack_id).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack not found")

    download_url, _ = create_pack_signed_url(pack.id)

    image_url = None
    if pack.image_path:
        image_url = f"{settings.base_url}/api/packs/{pack.id}/image"

    return {
        "name": pack.name,
        "description": pack.description or "",
        "image_url": image_url,
        "download_url": download_url,
    }
