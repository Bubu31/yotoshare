"""CRUD API for share packs (multi-archive sharing)."""

import io
import logging
import os
import secrets
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, require_permission
from app.config import get_settings
from app.database import get_db
from app.models import Archive, Pack, PackAsset, pack_archives
from app.schemas import PackCreate, PackResponse, PackUpdate, PackArchiveInfo
from app.services.pack_image import (
    delete_pack_image,
    get_pack_image_path,
    save_pack_image,
)
from app.services.storage import get_archive_path
from app.services.token import create_download_token, validate_pack_signed_token

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/packs", tags=["packs"])

PACK_EXPIRY_SECONDS = 30 * 24 * 3600  # 30 days


def _pack_to_response(pack: Pack) -> dict:
    return {
        "id": pack.id,
        "name": pack.name,
        "description": pack.description,
        "token": pack.token,
        "image_path": pack.image_path,
        "discord_post_id": pack.discord_post_id,
        "expires_at": pack.expires_at,
        "archive_count": len(pack.archives),
        "archives": [
            PackArchiveInfo(
                id=a.id,
                title=a.title,
                author=a.author,
                cover_path=a.cover_path,
                file_size=a.file_size,
            )
            for a in pack.archives
        ],
        "share_url": f"{settings.base_url}/pack/{pack.token}",
        "created_at": pack.created_at,
    }


async def _load_pack(db: AsyncSession, pack_id: int) -> Pack | None:
    result = await db.execute(
        select(Pack).where(Pack.id == pack_id).options(selectinload(Pack.archives))
    )
    return result.scalar_one_or_none()


# ── Static routes (MUST be before /{pack_id} to avoid shadowing) ──


VALID_ASSET_TYPES = ("background", "mascot")


@router.get("/assets")
async def list_assets(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "access")),
):
    """List current pack assets (background + mascot)."""
    result = await db.execute(select(PackAsset))
    assets = result.scalars().all()
    asset_map = {"background": None, "mascot": None}
    for asset in assets:
        if asset.asset_type in asset_map:
            asset_map[asset.asset_type] = asset.filename
    return asset_map


@router.post("/assets/{asset_type}")
async def upload_asset(
    asset_type: str,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "modify")),
):
    """Upload a pack asset (background or mascot)."""
    if asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(status_code=400, detail="Type invalide (background ou mascot)")

    content = await image.read()
    try:
        img = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Image invalide")

    os.makedirs(settings.pack_assets_path, exist_ok=True)

    result = await db.execute(select(PackAsset).where(PackAsset.asset_type == asset_type))
    existing = result.scalar_one_or_none()
    if existing:
        old_path = os.path.join(settings.pack_assets_path, existing.filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    if asset_type == "background":
        img = img.convert("RGB")
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(settings.pack_assets_path, filename)
        img.save(filepath, "JPEG", quality=95)
    else:
        if img.height > 400:
            ratio = 400 / img.height
            img = img.resize((int(img.width * ratio), 400), Image.Resampling.LANCZOS)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(settings.pack_assets_path, filename)
        img.save(filepath, "PNG")

    if existing:
        existing.filename = filename
    else:
        db.add(PackAsset(asset_type=asset_type, filename=filename))

    await db.commit()

    return {"asset_type": asset_type, "filename": filename}


@router.delete("/assets/{asset_type}", status_code=204)
async def delete_asset(
    asset_type: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "delete")),
):
    """Delete a pack asset."""
    if asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(status_code=400, detail="Type invalide (background ou mascot)")

    result = await db.execute(select(PackAsset).where(PackAsset.asset_type == asset_type))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset introuvable")

    filepath = os.path.join(settings.pack_assets_path, asset.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    await db.delete(asset)
    await db.commit()


@router.get("/assets/{asset_type}/image")
async def get_asset_image(asset_type: str, db: AsyncSession = Depends(get_db)):
    """Serve a pack asset image (no auth)."""
    if asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(status_code=400, detail="Type invalide")

    result = await db.execute(select(PackAsset).where(PackAsset.asset_type == asset_type))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset introuvable")

    filepath = os.path.join(settings.pack_assets_path, asset.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    media_type = "image/png" if asset.filename.endswith(".png") else "image/jpeg"
    return FileResponse(filepath, media_type=media_type)


@router.get("/signed-download/{signed_token}")
async def signed_download(signed_token: str, db: AsyncSession = Depends(get_db)):
    """Download all archives in a pack via a time-limited signed URL (no auth)."""
    pack_id = validate_pack_signed_token(signed_token)
    if pack_id is None:
        raise HTTPException(status_code=403, detail="Lien invalide ou expiré")

    pack = await _load_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    if not pack.archives:
        raise HTTPException(status_code=404, detail="Pack vide")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:
        for archive in pack.archives:
            archive_file = get_archive_path(archive.archive_path)
            if not archive_file:
                continue
            safe_name = "".join(
                c if c.isalnum() or c in " -_.()" else "_"
                for c in (archive.title or f"archive_{archive.id}")
            )
            ext = os.path.splitext(archive.archive_path)[1] or ".zip"
            zf.write(archive_file, f"{safe_name}{ext}")
            archive.download_count = (archive.download_count or 0) + 1

    await db.commit()

    buffer.seek(0)
    safe_pack_name = "".join(
        c if c.isalnum() or c in " -_.()" else "_"
        for c in pack.name
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_pack_name}.zip"',
        },
    )


@router.get("/by-token/{token}/download-all")
async def download_all(token: str, db: AsyncSession = Depends(get_db)):
    """Download all archives in a pack as a single ZIP (no auth)."""
    result = await db.execute(
        select(Pack).where(Pack.token == token).options(selectinload(Pack.archives))
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    now = datetime.now(timezone.utc)
    expires_at = pack.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=410, detail="Ce pack a expiré")

    if not pack.archives:
        raise HTTPException(status_code=404, detail="Pack vide")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:
        for archive in pack.archives:
            archive_file = get_archive_path(archive.archive_path)
            if not archive_file:
                continue
            safe_name = "".join(
                c if c.isalnum() or c in " -_.()" else "_"
                for c in (archive.title or f"archive_{archive.id}")
            )
            ext = os.path.splitext(archive.archive_path)[1] or ".zip"
            zf.write(archive_file, f"{safe_name}{ext}")
            archive.download_count = (archive.download_count or 0) + 1

    await db.commit()

    buffer.seek(0)
    safe_pack_name = "".join(
        c if c.isalnum() or c in " -_.()" else "_"
        for c in pack.name
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_pack_name}.zip"',
        },
    )


# ── Dynamic routes with {pack_id} ──


@router.post("", response_model=PackResponse)
async def create_pack(
    data: PackCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "access")),
):
    if not data.archive_ids:
        raise HTTPException(status_code=400, detail="Au moins une archive requise")

    result = await db.execute(select(Archive).where(Archive.id.in_(data.archive_ids)))
    archives = result.scalars().all()
    if len(archives) != len(data.archive_ids):
        raise HTTPException(status_code=404, detail="Une ou plusieurs archives introuvables")

    archive_map = {a.id: a for a in archives}
    ordered_archives = [archive_map[aid] for aid in data.archive_ids if aid in archive_map]

    token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=PACK_EXPIRY_SECONDS)

    cover_filenames = [a.cover_path for a in ordered_archives if a.cover_path]
    image_filename = await save_pack_image(data.name, cover_filenames, data.description, db=db)

    pack = Pack(
        name=data.name,
        description=data.description,
        token=token,
        image_path=image_filename,
        expires_at=expires_at,
        created_by=None,
    )
    db.add(pack)
    await db.flush()

    for pos, archive in enumerate(ordered_archives):
        await db.execute(
            pack_archives.insert().values(
                pack_id=pack.id, archive_id=archive.id, position=pos
            )
        )

    await db.commit()
    pack = await _load_pack(db, pack.id)

    return _pack_to_response(pack)


@router.get("")
async def list_packs(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "access")),
):
    count_result = await db.execute(select(func.count(Pack.id)))
    total = count_result.scalar()

    result = await db.execute(
        select(Pack)
        .options(selectinload(Pack.archives))
        .order_by(Pack.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    packs = result.scalars().all()
    return {"items": [_pack_to_response(p) for p in packs], "total": total}


@router.get("/{pack_id}", response_model=PackResponse)
async def get_pack(
    pack_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "access")),
):
    pack = await _load_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")
    return _pack_to_response(pack)


@router.put("/{pack_id}", response_model=PackResponse)
async def update_pack(
    pack_id: int,
    data: PackUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "modify")),
):
    pack = await _load_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    if data.name is not None:
        pack.name = data.name
    if data.description is not None:
        pack.description = data.description

    if data.archive_ids is not None:
        if not data.archive_ids:
            raise HTTPException(status_code=400, detail="Au moins une archive requise")

        result = await db.execute(select(Archive).where(Archive.id.in_(data.archive_ids)))
        archives = result.scalars().all()
        if len(archives) != len(data.archive_ids):
            raise HTTPException(status_code=404, detail="Une ou plusieurs archives introuvables")

        await db.execute(pack_archives.delete().where(pack_archives.c.pack_id == pack.id))

        archive_map = {a.id: a for a in archives}
        ordered_archives = [archive_map[aid] for aid in data.archive_ids if aid in archive_map]

        for pos, archive in enumerate(ordered_archives):
            await db.execute(
                pack_archives.insert().values(
                    pack_id=pack.id, archive_id=archive.id, position=pos
                )
            )

    if pack.image_path:
        delete_pack_image(pack.image_path)

    pack = await _load_pack(db, pack_id)
    cover_filenames = [a.cover_path for a in pack.archives if a.cover_path]
    pack.image_path = await save_pack_image(pack.name, cover_filenames, pack.description, db=db)

    await db.commit()
    pack = await _load_pack(db, pack_id)

    return _pack_to_response(pack)


@router.post("/{pack_id}/reshare", response_model=PackResponse)
async def reshare_pack(
    pack_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "access")),
):
    pack = await _load_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    pack.expires_at = datetime.now(timezone.utc) + timedelta(seconds=PACK_EXPIRY_SECONDS)
    await db.commit()
    pack = await _load_pack(db, pack_id)

    return _pack_to_response(pack)


@router.post("/{pack_id}/regenerate-image", response_model=PackResponse)
async def regenerate_pack_image(
    pack_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "modify")),
):
    """Regenerate the OG image for a pack."""
    pack = await _load_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    if pack.image_path:
        delete_pack_image(pack.image_path)

    cover_filenames = [a.cover_path for a in pack.archives if a.cover_path]
    pack.image_path = await save_pack_image(pack.name, cover_filenames, pack.description, db=db)

    await db.commit()
    pack = await _load_pack(db, pack_id)

    return _pack_to_response(pack)


@router.delete("/{pack_id}", status_code=204)
async def delete_pack(
    pack_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("packs", "delete")),
):
    pack = await _load_pack(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    if pack.image_path:
        delete_pack_image(pack.image_path)

    if pack.discord_post_id:
        try:
            from app.services.discord_client import delete_discord_thread
            delete_discord_thread(pack.discord_post_id)
        except Exception as e:
            logger.warning("Failed to delete Discord thread for pack %s: %s", pack.id, e)

    await db.delete(pack)
    await db.commit()


@router.get("/{pack_id}/image")
async def get_pack_og_image(pack_id: int, db: AsyncSession = Depends(get_db)):
    """Serve the OG image for crawlers (no auth required)."""
    result = await db.execute(select(Pack).where(Pack.id == pack_id))
    pack = result.scalar_one_or_none()
    if not pack or not pack.image_path:
        raise HTTPException(status_code=404, detail="Image introuvable")

    filepath = get_pack_image_path(pack.image_path)
    if not filepath:
        raise HTTPException(status_code=404, detail="Image introuvable")

    return FileResponse(filepath, media_type="image/jpeg")
