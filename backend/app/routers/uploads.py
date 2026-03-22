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
from app.models import UploadSession, Submission
from app import services
from app.services import discord_client
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads", tags=["uploads"])
settings = get_settings()


@router.post("/init")
async def init_upload(
    request: Request,
    filename: str = Form(...),
    total_size: int = Form(...),
    total_chunks: int = Form(...),
    chunk_size: int = Form(...),
    pseudonym: str = Form(None),
    parent_submission_id: int = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Initialize an upload session."""
    # Validate file size
    if total_size > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 500 MB).")

    # Validate .zip extension
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .zip sont acceptés.")

    # Get submitter IP
    submitter_ip = request.client.host if request.client else None

    # Check rate limit (5 submissions per hour per IP)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_submissions = await db.execute(
        select(Submission).where(
            (Submission.submitter_ip == submitter_ip) & (Submission.created_at > cutoff)
        )
    )
    if len(recent_submissions.scalars().all()) >= 5:
        raise HTTPException(status_code=429, detail="Trop de soumissions. Attendez 1 heure.")

    # Create upload session
    upload_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    session = UploadSession(
        upload_id=upload_id,
        filename=filename,
        total_size=total_size,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
        pseudonym=pseudonym.strip() if pseudonym else None,
        parent_submission_id=parent_submission_id,
        submitter_ip=submitter_ip,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    logger.info(f"Upload session created: {upload_id}, {total_chunks} chunks, {total_size} bytes")
    return {"upload_id": upload_id}


@router.post("/{upload_id}/chunk")
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single chunk."""
    # Verify session exists and is not expired
    result = await db.execute(
        select(UploadSession).where(UploadSession.upload_id == upload_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session d'upload introuvable.")

    if datetime.now(timezone.utc) > session.expires_at:
        # Clean up expired session
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=410, detail="Session d'upload expirée.")

    # Read chunk data
    chunk_data = await chunk.read()

    # Save chunk to disk (in thread pool)
    await asyncio.to_thread(
        services.storage.save_chunk, upload_id, chunk_index, chunk_data
    )

    logger.debug(f"Chunk {chunk_index} received for upload {upload_id}, size: {len(chunk_data)}")
    return {"received": chunk_index, "total": session.total_chunks}


@router.post("/{upload_id}/complete")
async def complete_upload(
    upload_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Complete the upload and create a submission."""
    # Verify session exists
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

    # Verify all chunks are present
    chunk_dir = services.storage.get_upload_chunks_dir(upload_id)
    if not all(
        os.path.exists(os.path.join(chunk_dir, f"chunk_{i:06d}"))
        for i in range(session.total_chunks)
    ):
        raise HTTPException(status_code=400, detail="Des chunks sont manquants.")

    try:
        # Assemble chunks into final ZIP file
        archive_filename, file_size = await asyncio.to_thread(
            services.storage.assemble_chunks, upload_id, session.total_chunks
        )

        # Extract and validate metadata
        archive_path = os.path.join(settings.archives_path, archive_filename)
        metadata = await asyncio.to_thread(
            services.storage.extract_archive_metadata, archive_path
        )

        # Create Submission record
        submission = Submission(
            pseudonym=session.pseudonym,
            title=metadata.get("title"),
            archive_path=archive_filename,
            file_size=file_size,
            total_duration=metadata.get("total_duration"),
            chapters_count=metadata.get("chapters_count"),
            chapters_data=json.dumps(metadata.get("chapters")) if metadata.get("chapters") else None,
            status="pending",
            submitter_ip=session.submitter_ip,
            parent_submission_id=session.parent_submission_id,
        )

        # Save cover if present
        if metadata.get("cover_data"):
            cover_filename = await services.storage.save_cover_from_bytes(
                metadata["cover_data"]
            )
            submission.cover_path = cover_filename

        db.add(submission)
        await db.commit()
        await db.refresh(submission)

        # Clean up chunks
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)

        # Delete upload session
        await db.delete(session)
        await db.commit()

        logger.info(
            f"Submission created via chunked upload - filename: '{session.filename}', "
            f"size: {file_size}, title: {metadata.get('title')}, upload_id: {upload_id}"
        )

        # Notify via Discord DM (fire-and-forget, don't block the response)
        try:
            await discord_client.notify_new_submission(
                submission_id=submission.id,
                title=metadata.get("title"),
                pseudonym=session.pseudonym,
                chapters_count=metadata.get("chapters_count"),
                file_size=file_size,
                is_rework=session.parent_submission_id is not None,
            )
        except Exception:
            logger.warning("Failed to send submission notification DM", exc_info=True)

        return {
            "message": "Votre archive a été soumise et sera examinée par un modérateur."
        }

    except Exception as e:
        logger.exception(f"Error during upload completion for {upload_id}")
        # Clean up chunks and session on error
        await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=500, detail="Erreur lors du traitement de l'archive.")


@router.delete("/{upload_id}")
async def cancel_upload(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an upload and clean up chunks."""
    result = await db.execute(
        select(UploadSession).where(UploadSession.upload_id == upload_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session d'upload introuvable.")

    # Clean up chunks
    await asyncio.to_thread(services.storage.cleanup_chunks, upload_id)

    # Delete session
    await db.delete(session)
    await db.commit()

    logger.info(f"Upload session cancelled: {upload_id}")
    return {"message": "Upload annulé."}
