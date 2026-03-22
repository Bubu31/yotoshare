import logging
import asyncio
import os
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import UploadSession, Archive, Category, Age
from app import services
from app.config import get_settings
from app.auth import require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/archives/upload", tags=["archive-uploads"])
settings = get_settings()


async def get_or_create_categories(db: AsyncSession, names: list[str]) -> list[Category]:
    """Get existing categories or create new ones by name."""
    names = [n.strip() for n in names if n.strip()]
    if not names:
        return []

    result = await db.execute(select(Category).where(Category.name.in_(names)))
    existing = {c.name: c for c in result.scalars().all()}

    categories = []
    for name in names:
        if name not in existing:
            cat = Category(name=name, icon="fas fa-folder")
            db.add(cat)
            await db.flush()
            await db.refresh(cat)
            existing[name] = cat
        categories.append(existing[name])
    return categories


async def get_or_create_ages(db: AsyncSession, names: list[str]) -> list[Age]:
    """Get existing ages or create new ones by name."""
    names = [n.strip() for n in names if n.strip()]
    if not names:
        return []

    result = await db.execute(select(Age).where(Age.name.in_(names)))
    existing = {a.name: a for a in result.scalars().all()}

    ages = []
    for name in names:
        if name not in existing:
            age = Age(name=name, icon="fas fa-child")
            db.add(age)
            await db.flush()
            await db.refresh(age)
            existing[name] = age
        ages.append(existing[name])
    return ages


@router.post("/init")
async def init_archive_upload(
    request: Request,
    filename: str = Form(...),
    total_size: int = Form(...),
    total_chunks: int = Form(...),
    chunk_size: int = Form(...),
    title: str = Form(None),
    author: str = Form(None),
    description: str = Form(None),
    categories: str = Form(None),
    ages: str = Form(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Initialize an archive upload session (admin/editor only)."""
    if total_size > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 500 MB).")

    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .zip sont acceptés.")

    submitter_ip = request.client.host if request.client else None

    # Create upload session
    upload_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    session = UploadSession(
        upload_id=upload_id,
        filename=filename,
        total_size=total_size,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
        pseudonym=json.dumps({
            "title": title,
            "author": author,
            "description": description,
            "categories": categories,
            "ages": ages,
        }),
        submitter_ip=submitter_ip,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    logger.info(f"Archive upload session created: {upload_id}, {total_chunks} chunks, {total_size} bytes")
    return {"upload_id": upload_id}


@router.post("/{upload_id}/chunk")
async def upload_archive_chunk(
    upload_id: str,
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Upload a single chunk."""
    result = await db.execute(
        select(UploadSession).where(UploadSession.upload_id == upload_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session d'upload introuvable.")

    if datetime.now(timezone.utc) > session.expires_at:
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=410, detail="Session d'upload expirée.")

    chunk_data = await chunk.read()
    await asyncio.to_thread(
        services.storage.save_chunk, upload_id, chunk_index, chunk_data
    )

    logger.debug(f"Chunk {chunk_index} received for archive upload {upload_id}, size: {len(chunk_data)}")
    return {"received": chunk_index, "total": session.total_chunks}


@router.post("/{upload_id}/complete")
async def complete_archive_upload(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Complete the upload and create an archive."""
    result = await db.execute(
        select(UploadSession).where(UploadSession.upload_id == upload_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session d'upload introuvable.")

    if datetime.now(timezone.utc) > session.expires_at:
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=410, detail="Session d'upload expirée.")

    chunk_dir = services.storage.get_upload_chunks_dir(upload_id)
    if not all(
        os.path.exists(os.path.join(chunk_dir, f"chunk_{i:06d}"))
        for i in range(session.total_chunks)
    ):
        raise HTTPException(status_code=400, detail="Des chunks sont manquants.")

    try:
        # Assemble chunks
        archive_filename, file_size = await asyncio.to_thread(
            services.storage.assemble_chunks, upload_id, session.total_chunks
        )

        archive_path = os.path.join(settings.archives_path, archive_filename)
        metadata = await asyncio.to_thread(
            services.storage.extract_archive_metadata, archive_path
        )

        # Parse metadata from session
        archive_meta = json.loads(session.pseudonym) if session.pseudonym else {}

        # Determine final title
        final_title = archive_meta.get("title") or metadata.get("title")
        if not final_title:
            raise HTTPException(status_code=400, detail="Title is required.")

        # Get or create categories
        category_list = []
        if archive_meta.get("categories"):
            try:
                category_names = json.loads(archive_meta["categories"]) if isinstance(archive_meta["categories"], str) else archive_meta["categories"]
                if isinstance(category_names, list):
                    category_list = await get_or_create_categories(db, category_names)
            except (json.JSONDecodeError, TypeError):
                pass

        # Get or create ages
        age_list = []
        if archive_meta.get("ages"):
            try:
                age_names = json.loads(archive_meta["ages"]) if isinstance(archive_meta["ages"], str) else archive_meta["ages"]
                if isinstance(age_names, list):
                    age_list = await get_or_create_ages(db, age_names)
            except (json.JSONDecodeError, TypeError):
                pass

        # Create Archive
        archive = Archive(
            title=final_title,
            author=archive_meta.get("author"),
            description=archive_meta.get("description"),
            archive_path=archive_filename,
            file_size=file_size,
            total_duration=metadata.get("total_duration"),
            chapters_count=metadata.get("chapters_count"),
            chapters_data=json.dumps(metadata.get("chapters")) if metadata.get("chapters") else None,
            categories=category_list,
            ages=age_list,
        )

        # Save cover if present
        if metadata.get("cover_data"):
            cover_filename = await services.storage.save_cover_from_bytes(
                metadata["cover_data"]
            )
            archive.cover_path = cover_filename

        db.add(archive)
        await db.commit()
        await db.refresh(archive)

        # Clean up
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
        await db.delete(session)
        await db.commit()

        logger.info(
            f"Archive created via chunked upload - filename: '{session.filename}', "
            f"size: {file_size}, title: {archive.title}, upload_id: {upload_id}"
        )

        return {
            "message": "Archive créée avec succès.",
            "archive_id": archive.id,
        }

    except Exception as e:
        logger.exception(f"Error during archive upload completion for {upload_id}")
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=500, detail="Erreur lors du traitement de l'archive.")


@router.delete("/{upload_id}")
async def cancel_archive_upload(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Cancel an archive upload."""
    result = await db.execute(
        select(UploadSession).where(UploadSession.upload_id == upload_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session d'upload introuvable.")

    await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
    await db.delete(session)
    await db.commit()

    logger.info(f"Archive upload cancelled: {upload_id}")
    return {"message": "Upload annulé."}
