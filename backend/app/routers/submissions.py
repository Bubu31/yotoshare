import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Submission, Archive
from app.schemas import SubmissionResponse, SubmissionReviewRequest
from app.auth import require_permission
from app.services import storage
from app.services import archive_editor
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/submissions", tags=["submissions"])

# In-memory rate limiting
_rate: dict[str, list[float]] = defaultdict(list)
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
    db: Session = Depends(get_db),
):
    """Public endpoint: submit a MYO archive for moderation."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # Validate extension
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers .zip sont acceptés.",
        )

    # Save archive
    filename, file_size = await storage.save_archive(file)

    if file_size > MAX_FILE_SIZE:
        storage.delete_archive(filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier trop volumineux (max 500 MB).",
        )

    # Extract metadata and validate MYO format
    archive_path = storage.get_archive_path(filename)
    metadata = storage.extract_archive_metadata(archive_path)

    if not metadata.get("title") and not metadata.get("chapters"):
        # No card-data.json found → not a valid MYO archive
        storage.delete_archive(filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archive invalide : pas de card-data.json trouvé. Seules les archives MYO sont acceptées.",
        )

    # Save cover thumbnail if present
    cover_filename = None
    if metadata.get("cover_data"):
        cover_filename = await storage.save_cover_from_bytes(metadata["cover_data"])

    # Create submission
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
    )
    db.add(submission)
    db.commit()

    return {"message": "Votre archive a été soumise et sera examinée par un modérateur. Merci !"}


@router.get("", response_model=list[SubmissionResponse])
async def list_submissions(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """List submissions with optional status filter."""
    query = db.query(Submission)
    if status_filter:
        query = query.filter(Submission.status == status_filter)
    query = query.order_by(Submission.created_at.desc())
    return query.all()


@router.get("/count")
async def count_pending(
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Count pending submissions (for badge)."""
    count = db.query(Submission).filter(Submission.status == "pending").count()
    return {"count": count}


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Get a single submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")
    return submission


@router.get("/{submission_id}/cover")
async def get_submission_cover(
    submission_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Get submission cover image."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission or not submission.cover_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover introuvable")

    cover_path = storage.get_cover_path(submission.cover_path)
    if not cover_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier cover introuvable")

    with open(cover_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/jpeg")


@router.get("/{submission_id}/content")
async def get_submission_content(
    submission_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Get submission archive content (chapters, audio info, icons)."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    archive_path = storage.get_archive_path(submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    try:
        content = archive_editor.get_archive_content(archive_path)
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


@router.get("/{submission_id}/audio/{chapter_key}")
async def get_submission_audio(
    submission_id: int,
    chapter_key: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Stream a chapter's audio from a submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    archive_path = storage.get_archive_path(submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    try:
        result = archive_editor.get_chapter_audio_path_from_archive(archive_path, chapter_key)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio introuvable")

        temp_dir, audio_path, editor = result

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        editor.cleanup()

        ext = os.path.splitext(audio_path)[1].lower()
        content_type = "audio/mpeg"
        if ext == ".m4a":
            content_type = "audio/mp4"
        elif ext == ".ogg":
            content_type = "audio/ogg"
        elif ext == ".wav":
            content_type = "audio/wav"

        return Response(content=audio_data, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{submission_id}/icon/{chapter_key}")
async def get_submission_icon(
    submission_id: int,
    chapter_key: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "access")),
):
    """Get a chapter's icon from a submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    archive_path = storage.get_archive_path(submission.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier archive introuvable")

    try:
        icon_data = archive_editor.get_chapter_icon(archive_path, chapter_key)
        if not icon_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Icône introuvable")
        return Response(content=icon_data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{submission_id}/review")
async def review_submission(
    submission_id: int,
    review: SubmissionReviewRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("submissions", "modify")),
):
    """Approve or reject a submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    if submission.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette soumission a déjà été traitée.",
        )

    if review.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action invalide. Utilisez 'approve' ou 'reject'.",
        )

    # Get reviewer user id from token
    from app.models import User
    reviewer = db.query(User).filter(User.username == user.get("username")).first()
    reviewer_id = reviewer.id if reviewer else None

    if review.action == "approve":
        # Create an Archive from the submission
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
        db.commit()

        return {"message": "Soumission approuvée. L'archive a été ajoutée à la bibliothèque.", "archive_id": archive.id}

    else:  # reject
        # Delete files
        storage.delete_archive(submission.archive_path)
        if submission.cover_path:
            storage.delete_cover(submission.cover_path)

        submission.status = "rejected"
        submission.reviewer_id = reviewer_id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.rejection_reason = review.rejection_reason
        db.commit()

        return {"message": "Soumission rejetée."}


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("submissions", "delete")),
):
    """Delete a submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soumission introuvable")

    # Only delete files if not approved (approved files belong to the archive now)
    if submission.status != "approved":
        storage.delete_archive(submission.archive_path)
        if submission.cover_path:
            storage.delete_cover(submission.cover_path)

    db.delete(submission)
    db.commit()
