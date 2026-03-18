import asyncio
import json
import logging
import os
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.models import Submission, Archive, User
from app.schemas import SubmissionResponse, SubmissionReviewRequest, ReworkSubmissionResponse
from app.auth import require_permission
from app.services import storage
from app.services import archive_editor
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/submissions", tags=["submissions"])

# In-memory rate limiting
_rate = defaultdict(list)  # ip -> [timestamps]
MAX_PER_HOUR = 5
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


def _check_rate_limit(ip: str):
    now = time.time()
    cutoff = now - 3600
    _rate[ip] = [t for t in _rate[ip] if t > cutoff]
    if len(_rate[ip]) >= MAX_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de soumissions. Réessayez plus tard.",
        )
    _rate[ip].append(now)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_submission(
    request: Request,
    file: UploadFile = File(...),
    pseudonym: Optional[str] = Form(None),
    parent_submission_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: submit a MYO archive for moderation."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if parent_submission_id is not None:
        result = await db.execute(select(Submission).where(Submission.id == parent_submission_id))
        parent = result.scalar_one_or_none()
        if not parent or parent.status != "rework":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Soumission parente introuvable ou non en statut rework.",
            )

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers .zip sont acceptés.",
        )

    filename, file_size = await storage.save_archive(file)

    if file_size > MAX_FILE_SIZE:
        storage.delete_archive(filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier trop volumineux (max 500 MB).",
        )

    archive_path = storage.get_archive_path(filename)
    metadata = storage.extract_archive_metadata(archive_path)

    if not metadata.get("title") and not metadata.get("chapters"):
        storage.delete_archive(filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archive invalide : pas de card-data.json trouvé. Seules les archives MYO sont acceptées.",
        )

    cover_filename = None
    if metadata.get("cover_data"):
        cover_filename = await storage.save_cover_from_bytes(metadata["cover_data"])

    # Extract ZIP contents to disk for fast access during review
    await asyncio.to_thread(storage.extract_submission_data, archive_path, filename)

    submission = Submission(
        pseudonym=pseudonym.strip() if pseudonym else None,
        title=metadata.get("title"),
        cover_path=cover_filename,
        archive_path=filename,
        file_size=file_size,
        total_duration=metadata.get("total_duration"),
        chapters_count=metadata.get("chapters_count"),
        chapters_data=json.dumps(metadata["chapters"]) if metadata.get("chapters") else None,
        status="pending",
        submitter_ip=client_ip,
        parent_submission_id=parent_submission_id,
    )
    db.add(submission)
    await db.commit()

    return {"message": "Votre archive a été soumise et sera examinée par un modérateur. Merci !"}


def _enrich_submission(sub: Submission) -> dict:
    """Add has_extracted_data to a submission ORM object."""
    data = {c.name: getattr(sub, c.name) for c in sub.__table__.columns}
    data["has_extracted_data"] = storage.get_submission_data_dir(sub.archive_path) is not None
    return data


@router.get("", response_model=List[SubmissionResponse])
async def list_submissions(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    stmt = select(Submission)
    if status_filter:
        stmt = stmt.where(Submission.status == status_filter)
    stmt = stmt.order_by(Submission.created_at.desc())
    result = await db.execute(stmt)
    return [_enrich_submission(s) for s in result.scalars().all()]


@router.get("/submissions-count")
async def count_pending(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    result = await db.execute(
        select(func.count(Submission.id)).where(Submission.status == "pending")
    )
    return {"count": result.scalar()}


@router.get("/rework", response_model=List[ReworkSubmissionResponse])
async def list_rework_submissions(
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: list submissions that need rework."""
    stmt = (
        select(Submission)
        .where(Submission.status == "rework")
        .order_by(Submission.reviewed_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/rework/{submission_id}/download")
async def download_rework_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: download a rework submission ZIP."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission or submission.status != "rework":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    archive_path = await asyncio.to_thread(storage.get_archive_path, submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    filename = f"{submission.title or 'archive'}.zip"

    async def file_iterator():
        async with aiofiles.open(archive_path, "rb") as f:
            while chunk := await f.read(64 * 1024):
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")
    return _enrich_submission(submission)


@router.get("/{submission_id}/cover")
async def get_submission_cover(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission or not submission.cover_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover introuvable")

    cover_path = storage.get_cover_path(submission.cover_path)
    if not cover_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier cover introuvable")

    async with aiofiles.open(cover_path, "rb") as f:
        data = await f.read()
    return Response(content=data, media_type="image/jpeg")


@router.get("/{submission_id}/content")
async def get_submission_content(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    # Try extracted data first (fast path)
    data_dir = storage.get_submission_data_dir(submission.archive_path)
    if data_dir:
        card_data_path = os.path.join(data_dir, "card-data.json")
        if os.path.exists(card_data_path):
            try:
                with open(card_data_path, "r", encoding="utf-8") as f:
                    card_data = json.load(f)

                icons_dir = os.path.join(data_dir, "icons")
                audio_dir = os.path.join(data_dir, "audio")
                has_cover = any(
                    os.path.exists(os.path.join(data_dir, f"cover{ext}"))
                    for ext in (".jpg", ".png")
                )

                chapters = []
                for i, ch in enumerate(card_data.get("content", {}).get("chapters", [])):
                    key = ch.get("key") or f"chapter_{i}"
                    icon_file = None
                    for ext in (".png", ".jpg", ".jpeg"):
                        if os.path.exists(os.path.join(icons_dir, f"{key}{ext}")):
                            icon_file = f"{key}{ext}"
                            break
                    audio_file = None
                    for ext in (".m4a", ".mp3", ".m4b", ".aac", ".wav", ".flac", ".ogg", ".opus"):
                        if os.path.exists(os.path.join(audio_dir, f"{key}{ext}")):
                            audio_file = f"{key}{ext}"
                            break

                    duration = ch.get("duration")
                    if duration and duration < 100000:
                        duration = duration * 1000

                    chapters.append({
                        "key": key,
                        "title": ch.get("title"),
                        "label": ch.get("overlayLabel"),
                        "duration": duration,
                        "audio_file": audio_file,
                        "icon_file": icon_file,
                        "order": i,
                    })

                return {
                    "id": submission.id,
                    "title": submission.title,
                    "chapters": chapters,
                    "has_cover": has_cover,
                }
            except Exception as e:
                logger.warning("Error reading extracted data, falling back to ZIP: %s", e)

    # Fallback: read from ZIP (for old submissions without extracted data)
    archive_path = await asyncio.to_thread(storage.get_archive_path, submission.archive_path)
    if archive_path:
        try:
            content = await asyncio.to_thread(archive_editor.get_archive_content, archive_path)
            chapters = [
                {
                    "key": ch.get("key") or f"chapter_{i}",
                    "title": ch.get("title"),
                    "label": ch.get("label"),
                    "duration": ch.get("duration"),
                    "audio_file": ch.get("audio_file"),
                    "icon_file": ch.get("icon_file"),
                    "order": ch.get("order", i),
                }
                for i, ch in enumerate(content.get("chapters", []))
            ]
            return {
                "id": submission.id,
                "title": submission.title,
                "chapters": chapters,
                "has_cover": content.get("has_cover", False),
            }
        except Exception as e:
            logger.exception("Error loading submission content")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    logger.warning("Archive file not found for submission %d, using cached chapters_data", submission_id)
    chapters = []
    if submission.chapters_data:
        try:
            cached = json.loads(submission.chapters_data)
            chapters = [
                {
                    "key": ch.get("key") or f"chapter_{i}",
                    "title": ch.get("title"),
                    "label": ch.get("label"),
                    "duration": ch.get("duration"),
                    "audio_file": None,
                    "icon_file": None,
                    "order": i,
                }
                for i, ch in enumerate(cached)
            ]
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": submission.id,
        "title": submission.title,
        "chapters": chapters,
        "has_cover": bool(submission.cover_path),
        "archive_missing": True,
    }


@router.get("/{submission_id}/audio/{chapter_key}")
async def get_submission_audio(
    submission_id: int,
    chapter_key: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    # Try extracted data first (fast path)
    data_dir = storage.get_submission_data_dir(submission.archive_path)
    if data_dir:
        audio_dir = os.path.join(data_dir, "audio")
        for ext in (".m4a", ".mp3", ".m4b", ".aac", ".wav", ".flac", ".ogg", ".opus"):
            audio_path = os.path.join(audio_dir, f"{chapter_key}{ext}")
            if os.path.exists(audio_path):
                content_types = {
                    ".m4a": "audio/mp4", ".m4b": "audio/mp4", ".aac": "audio/mp4",
                    ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".opus": "audio/ogg",
                    ".wav": "audio/wav", ".flac": "audio/flac",
                }
                return FileResponse(audio_path, media_type=content_types.get(ext, "audio/mpeg"))

    # Fallback: extract from ZIP
    archive_path = await asyncio.to_thread(storage.get_archive_path, submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    try:
        result = await asyncio.to_thread(archive_editor.get_chapter_audio_path_from_archive, archive_path, chapter_key)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio introuvable")

        temp_dir, audio_path, editor = result

        ext = os.path.splitext(audio_path)[1].lower()
        content_type = "audio/mpeg"
        if ext == ".m4a":
            content_type = "audio/mp4"
        elif ext == ".ogg":
            content_type = "audio/ogg"
        elif ext == ".wav":
            content_type = "audio/wav"

        async def audio_iterator():
            try:
                async with aiofiles.open(audio_path, "rb") as f:
                    while chunk := await f.read(64 * 1024):
                        yield chunk
            finally:
                editor.cleanup()

        return StreamingResponse(audio_iterator(), media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{submission_id}/icon/{chapter_key}")
async def get_submission_icon(
    submission_id: int,
    chapter_key: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    # Try extracted data first (fast path)
    data_dir = storage.get_submission_data_dir(submission.archive_path)
    if data_dir:
        icons_dir = os.path.join(data_dir, "icons")
        for ext in (".png", ".jpg", ".jpeg"):
            icon_path = os.path.join(icons_dir, f"{chapter_key}{ext}")
            if os.path.exists(icon_path):
                media_type = "image/png" if ext == ".png" else "image/jpeg"
                return FileResponse(icon_path, media_type=media_type)

    # Fallback: read from ZIP
    archive_path = await asyncio.to_thread(storage.get_archive_path, submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    def _read_icon_sync(path: str, key: str):
        with zipfile.ZipFile(path, "r") as zf:
            namelist = zf.namelist()

            card_data_paths = [n for n in namelist if n.endswith("data/card-data.json")]
            if not card_data_paths:
                return None, None

            with zf.open(card_data_paths[0]) as f:
                card_data = json.load(f)

            chapters = card_data.get("content", {}).get("chapters", [])
            chapter = None
            chapter_index = None
            for i, ch in enumerate(chapters):
                if ch.get("key") == key:
                    chapter = ch
                    chapter_index = i
                    break

            if chapter is None:
                return None, None

            icon_filename = chapter.get("display", {}).get("icon16x16") if chapter.get("display") else None
            if icon_filename and icon_filename.startswith("yoto:"):
                icon_filename = None

            icon_entries = [n for n in namelist if ("icons/" in n) and n.lower().endswith((".png", ".jpg", ".jpeg"))]
            icon_entries.sort()

            matched_entry = None
            if icon_filename:
                for entry in icon_entries:
                    if entry.endswith(f"/{icon_filename}") or entry.endswith(f"\\{icon_filename}"):
                        matched_entry = entry
                        break

            if not matched_entry:
                for entry in icon_entries:
                    basename = entry.split("/")[-1]
                    if basename.startswith(f"{key}-") or basename.startswith(f"{key} -"):
                        matched_entry = entry
                        break

            if not matched_entry and chapter_index is not None and chapter_index < len(icon_entries):
                matched_entry = icon_entries[chapter_index]

            if not matched_entry:
                return None, None

            icon_data = zf.read(matched_entry)
            media_type = "image/png" if matched_entry.lower().endswith(".png") else "image/jpeg"
            return icon_data, media_type

    try:
        icon_data, media_type = await asyncio.to_thread(_read_icon_sync, archive_path, chapter_key)
        if icon_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Icône introuvable")
        return Response(content=icon_data, media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{submission_id}/extract")
async def extract_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Extract submission ZIP to disk for fast consultation."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    if storage.get_submission_data_dir(submission.archive_path):
        return {"message": "Données déjà extraites."}

    archive_path = await asyncio.to_thread(storage.get_archive_path, submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    dest = await asyncio.to_thread(storage.extract_submission_data, archive_path, submission.archive_path)
    if not dest:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de l'extraction")

    return {"message": "Extraction terminée."}


@router.post("/{submission_id}/review")
async def review_submission(
    submission_id: int,
    review: SubmissionReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("submissions", "modify")),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    if submission.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette soumission a déjà été traitée.",
        )

    if review.action not in ("approve", "reject", "rework"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action invalide. Utilisez 'approve', 'reject' ou 'rework'.",
        )

    if review.action == "rework" and not review.rework_comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un commentaire est requis pour demander un rework.",
        )

    result = await db.execute(select(User).where(User.username == user.get("username")))
    reviewer = result.scalar_one_or_none()
    reviewer_id = reviewer.id if reviewer else None

    if review.action == "approve":
        archive = Archive(
            title=submission.title or "Sans titre",
            author=submission.pseudonym,
            cover_path=submission.cover_path,
            archive_path=submission.archive_path,
            file_size=submission.file_size,
            total_duration=submission.total_duration,
            chapters_count=submission.chapters_count,
            chapters_data=submission.chapters_data,
        )
        db.add(archive)

        submission.status = "approved"
        submission.reviewer_id = reviewer_id
        submission.reviewed_at = datetime.now(timezone.utc)

        # If this is a re-submission, resolve the parent
        if submission.parent_submission_id:
            parent_result = await db.execute(
                select(Submission).where(Submission.id == submission.parent_submission_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent and parent.status == "rework":
                storage.delete_archive(parent.archive_path)
                storage.delete_submission_data(parent.archive_path)
                if parent.cover_path:
                    storage.delete_cover(parent.cover_path)
                parent.status = "rework_resolved"

        # Clean up extracted submission data (archive is now in the library)
        storage.delete_submission_data(submission.archive_path)

        await db.commit()
        await db.refresh(archive)

        return {"message": "Soumission approuvée. L'archive a été ajoutée à la bibliothèque.", "archive_id": archive.id}

    elif review.action == "rework":
        submission.status = "rework"
        submission.reviewer_id = reviewer_id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.rework_comment = review.rework_comment
        await db.commit()

        return {"message": "Soumission marquée comme à retravailler."}

    else:  # reject
        storage.delete_archive(submission.archive_path)
        storage.delete_submission_data(submission.archive_path)
        if submission.cover_path:
            storage.delete_cover(submission.cover_path)

        submission.status = "rejected"
        submission.reviewer_id = reviewer_id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.rejection_reason = review.rejection_reason
        await db.commit()

        return {"message": "Soumission rejetée."}


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "delete")),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    if submission.status != "approved":
        storage.delete_archive(submission.archive_path)
        storage.delete_submission_data(submission.archive_path)
        if submission.cover_path:
            storage.delete_cover(submission.cover_path)

    await db.delete(submission)
    await db.commit()
