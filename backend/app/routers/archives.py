import io
import json
import logging
import math
import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from PIL import Image
from app.database import get_db
from app.models import Archive, Category, Age
from app.schemas import (
    ArchiveResponse, ArchiveListResponse, ArchiveUpdate,
    ArchiveContent, ChapterDetail, ChaptersUpdateRequest,
    SplitRequest, TrimRequest, MergeRequest, NfoUpdateRequest, WaveformResponse
)
from app.auth import require_permission
from app.services import storage
from app.services.discord_bot import delete_discord_thread, edit_discord_thread
from app.services import archive_editor
from app.services import audio_processor
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/archives", tags=["archives"])


def get_or_create_categories(db: Session, category_names: List[str]) -> List[Category]:
    """Get existing categories or create new ones by name"""
    categories = []
    for name in category_names:
        name = name.strip()
        if not name:
            continue
        category = db.query(Category).filter(Category.name == name).first()
        if not category:
            category = Category(name=name, icon="fas fa-folder")
            db.add(category)
            db.flush()
        categories.append(category)
    return categories


def get_or_create_ages(db: Session, age_names: List[str]) -> List[Age]:
    """Get existing ages or create new ones by name"""
    ages = []
    for name in age_names:
        name = name.strip()
        if not name:
            continue
        age = db.query(Age).filter(Age.name == name).first()
        if not age:
            age = Age(name=name, icon="fas fa-child")
            db.add(age)
            db.flush()
        ages.append(age)
    return ages


@router.get("")
async def list_archives(
    category_id: Optional[int] = None,
    age_id: Optional[int] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "date-desc",
    hide_published: Optional[bool] = False,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Archive)
    if category_id:
        query = query.filter(Archive.categories.any(Category.id == category_id))
    if age_id:
        query = query.filter(Archive.ages.any(Age.id == age_id))
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Archive.title.ilike(search_term)) | (Archive.author.ilike(search_term))
        )
    if hide_published:
        query = query.filter(Archive.discord_post_id.is_(None))

    total = query.count()

    sort_map = {
        "date-desc": Archive.created_at.desc(),
        "date-asc": Archive.created_at.asc(),
        "alpha-asc": Archive.title.asc(),
        "alpha-desc": Archive.title.desc(),
        "downloads-desc": Archive.download_count.desc(),
        "downloads-asc": Archive.download_count.asc(),
    }
    order = sort_map.get(sort, Archive.created_at.desc())
    items = query.order_by(order).offset(offset).limit(limit).all()

    return {"items": items, "total": total}


def archive_to_response(archive: Archive) -> dict:
    """Convert archive model to response dict with parsed chapters"""
    chapters = None
    if archive.chapters_data:
        try:
            chapters = json.loads(archive.chapters_data)
        except json.JSONDecodeError:
            pass

    return {
        "id": archive.id,
        "title": archive.title,
        "author": archive.author,
        "description": archive.description,
        "cover_path": archive.cover_path,
        "archive_path": archive.archive_path,
        "file_size": archive.file_size,
        "total_duration": archive.total_duration,
        "chapters_count": archive.chapters_count,
        "chapters": chapters,
        "discord_post_id": archive.discord_post_id,
        "download_count": archive.download_count or 0,
        "created_at": archive.created_at,
        "updated_at": archive.updated_at,
        "categories": archive.categories,
        "ages": archive.ages,
    }


@router.get("/grid-visual")
async def generate_grid_visual(
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Generate a mosaic image of all covers from archives published on Discord."""
    archives = (
        db.query(Archive)
        .filter(Archive.discord_post_id.isnot(None))
        .order_by(Archive.title)
        .all()
    )

    if not archives:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published archives found",
        )

    # Grid settings
    cell_w, cell_h = 150, 200
    padding = 8
    bg_color = (26, 26, 46)  # #1a1a2e

    count = len(archives)
    cols = min(max(int(math.ceil(math.sqrt(count))), 1), 10)
    rows = math.ceil(count / cols)

    img_w = cols * cell_w + (cols + 1) * padding
    img_h = rows * cell_h + (rows + 1) * padding

    grid = Image.new("RGB", (img_w, img_h), bg_color)

    for idx, archive in enumerate(archives):
        if not archive.cover_path:
            continue

        cover_file = storage.get_cover_path(archive.cover_path)
        if not cover_file or not os.path.exists(cover_file):
            continue

        try:
            cover = Image.open(cover_file)
            cover = cover.resize((cell_w, cell_h), Image.LANCZOS)

            row, col = divmod(idx, cols)
            x = padding + col * (cell_w + padding)
            y = padding + row * (cell_h + padding)
            grid.paste(cover, (x, y))
        except Exception:
            logger.warning("Failed to process cover for archive %s", archive.id)
            continue

    buf = io.BytesIO()
    grid.save(buf, format="JPEG", quality=90)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/jpeg",
        headers={"Content-Disposition": "attachment; filename=grid-visual.jpg"},
    )


@router.get("/{archive_id}", response_model=ArchiveResponse)
async def get_archive(archive_id: int, db: Session = Depends(get_db)):
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")
    return archive_to_response(archive)


@router.post("", response_model=ArchiveResponse, status_code=status.HTTP_201_CREATED)
async def create_archive(
    archive_file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),  # JSON array of category names
    ages: Optional[str] = Form(None),  # JSON array of age names
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    if not archive_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archive must be a .zip file"
        )

    archive_filename, file_size = await storage.save_archive(archive_file)

    # Extract metadata from archive
    archive_path = storage.get_archive_path(archive_filename)
    metadata = storage.extract_archive_metadata(archive_path)

    # Use extracted title if not provided
    final_title = title if title else metadata.get("title")
    if not final_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required. It was not found in the archive and not provided."
        )

    # Extract cover from archive
    cover_filename = None
    if metadata.get("cover_data"):
        cover_filename = await storage.save_cover_from_bytes(metadata["cover_data"])

    # Parse and get/create categories
    category_list = []
    if categories:
        try:
            category_names = json.loads(categories)
            if isinstance(category_names, list):
                category_list = get_or_create_categories(db, category_names)
        except json.JSONDecodeError:
            pass

    # Parse and get/create ages
    age_list = []
    if ages:
        try:
            age_names = json.loads(ages)
            if isinstance(age_names, list):
                age_list = get_or_create_ages(db, age_names)
        except json.JSONDecodeError:
            pass

    # Prepare chapters data as JSON string
    chapters_json = None
    if metadata.get("chapters"):
        chapters_json = json.dumps(metadata["chapters"])

    archive = Archive(
        title=final_title,
        author=author,
        description=description,
        archive_path=archive_filename,
        cover_path=cover_filename,
        file_size=file_size,
        total_duration=metadata.get("total_duration"),
        chapters_count=metadata.get("chapters_count"),
        chapters_data=chapters_json,
        categories=category_list,
        ages=age_list,
    )
    db.add(archive)
    db.commit()
    db.refresh(archive)
    return archive_to_response(archive)


@router.put("/{archive_id}", response_model=ArchiveResponse)
async def update_archive(
    archive_id: int,
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),  # JSON array of category names
    ages: Optional[str] = Form(None),  # JSON array of age names
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    if title is not None:
        archive.title = title
    if author is not None:
        archive.author = author
    if description is not None:
        archive.description = description

    # Update categories if provided
    if categories is not None:
        try:
            category_names = json.loads(categories)
            if isinstance(category_names, list):
                archive.categories = get_or_create_categories(db, category_names)
        except json.JSONDecodeError:
            pass

    # Update ages if provided
    if ages is not None:
        try:
            age_names = json.loads(ages)
            if isinstance(age_names, list):
                archive.ages = get_or_create_ages(db, age_names)
        except json.JSONDecodeError:
            pass

    db.commit()
    db.refresh(archive)

    # Sync with Discord if published
    if archive.discord_post_id:
        try:
            cover_url = None
            if archive.cover_path:
                cover_url = f"{settings.base_url}/api/archives/cover/{archive.cover_path}"

            chapters = None
            if archive.chapters_data:
                try:
                    chapters = json.loads(archive.chapters_data)
                except json.JSONDecodeError:
                    pass

            # Get tag names (categories + ages)
            tag_names = []
            if archive.categories:
                tag_names.extend([cat.name for cat in archive.categories])
            if archive.ages:
                tag_names.extend([age.name for age in archive.ages])

            edit_discord_thread(
                thread_id=archive.discord_post_id,
                title=archive.title,
                author=archive.author or "",
                description=archive.description or "",
                cover_url=cover_url,
                file_size=archive.file_size,
                total_duration=archive.total_duration,
                chapters_count=archive.chapters_count,
                chapters=chapters,
                categories=tag_names if tag_names else None,
                archive_id=archive.id,
            )
        except Exception as e:
            logger.warning("Failed to sync with Discord: %s", e)
            # Continue even if Discord sync fails

    return archive_to_response(archive)


@router.put("/{archive_id}/cover", response_model=ArchiveResponse)
async def update_archive_cover(
    archive_id: int,
    cover_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    if archive.cover_path:
        storage.delete_cover(archive.cover_path)

    cover_filename = await storage.save_cover(cover_file)
    archive.cover_path = cover_filename
    db.commit()
    db.refresh(archive)

    # Sync with Discord if published
    if archive.discord_post_id:
        try:
            cover_url = f"{settings.base_url}/api/archives/cover/{archive.cover_path}"

            chapters = None
            if archive.chapters_data:
                try:
                    chapters = json.loads(archive.chapters_data)
                except json.JSONDecodeError:
                    pass

            tag_names = []
            if archive.categories:
                tag_names.extend([cat.name for cat in archive.categories])
            if archive.ages:
                tag_names.extend([age.name for age in archive.ages])

            edit_discord_thread(
                thread_id=archive.discord_post_id,
                title=archive.title,
                author=archive.author or "",
                description=archive.description or "",
                cover_url=cover_url,
                file_size=archive.file_size,
                total_duration=archive.total_duration,
                chapters_count=archive.chapters_count,
                chapters=chapters,
                categories=tag_names if tag_names else None,
                archive_id=archive.id,
            )
        except Exception as e:
            logger.warning("Failed to sync cover with Discord: %s", e)

    return archive_to_response(archive)


@router.delete("/{archive_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_archive(
    archive_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "delete")),
):
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    # Delete Discord thread if it exists
    if archive.discord_post_id:
        try:
            delete_discord_thread(archive.discord_post_id)
        except Exception as e:
            logger.warning("Failed to delete Discord thread: %s", e)
            # Continue with archive deletion even if Discord fails

    storage.delete_archive(archive.archive_path)
    if archive.cover_path:
        storage.delete_cover(archive.cover_path)

    db.delete(archive)
    db.commit()


@router.get("/cover/{filename}")
async def get_cover(filename: str):
    filepath = storage.get_cover_path(filename)
    if not filepath:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
    return FileResponse(filepath, media_type="image/jpeg")


# ============================================
# Archive Editor Endpoints
# ============================================


def sync_archive_metadata(archive: Archive, db: Session):
    """Re-extract and sync metadata from archive file to database."""
    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        return

    metadata = storage.extract_archive_metadata(archive_path)

    # Update database
    if metadata.get("chapters"):
        archive.chapters_data = json.dumps(metadata["chapters"])
        archive.chapters_count = len(metadata["chapters"])
    if metadata.get("total_duration") is not None:
        archive.total_duration = metadata["total_duration"]

    # Update file size
    archive.file_size = os.path.getsize(archive_path)

    db.commit()
    db.refresh(archive)


def sync_discord_after_edit(archive: Archive):
    """Sync with Discord after archive edit."""
    if not archive.discord_post_id:
        return

    try:
        cover_url = None
        if archive.cover_path:
            cover_url = f"{settings.base_url}/api/archives/cover/{archive.cover_path}"

        chapters = None
        if archive.chapters_data:
            try:
                chapters = json.loads(archive.chapters_data)
            except json.JSONDecodeError:
                pass

        tag_names = []
        if archive.categories:
            tag_names.extend([cat.name for cat in archive.categories])
        if archive.ages:
            tag_names.extend([age.name for age in archive.ages])

        edit_discord_thread(
            thread_id=archive.discord_post_id,
            title=archive.title,
            author=archive.author or "",
            description=archive.description or "",
            cover_url=cover_url,
            file_size=archive.file_size,
            total_duration=archive.total_duration,
            chapters_count=archive.chapters_count,
            chapters=chapters,
            categories=tag_names if tag_names else None,
            archive_id=archive.id,
        )
    except Exception as e:
        logger.warning("Failed to sync with Discord: %s", e)


@router.get("/{archive_id}/content", response_model=ArchiveContent)
async def get_archive_content(
    archive_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Get detailed archive content including chapters with audio info."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        logger.debug("Loading archive content from: %s", archive_path)
        content = archive_editor.get_archive_content(archive_path)
        logger.debug("Got content with %d chapters", len(content.get('chapters', [])))

        chapters = [
            ChapterDetail(
                key=ch.get("key") or f"chapter_{i}",
                title=ch.get("title"),
                label=ch.get("label"),
                duration=ch.get("duration"),
                audio_file=ch.get("audio_file"),
                icon_file=ch.get("icon_file"),
                order=ch.get("order", i),
            )
            for i, ch in enumerate(content.get("chapters", []))
        ]

        return ArchiveContent(
            id=archive.id,
            title=archive.title,
            chapters=chapters,
            has_cover=content.get("has_cover", False),
            nfo=content.get("nfo"),
        )
    except Exception as e:
        logger.exception("Error loading archive content")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{archive_id}/chapters", response_model=ArchiveResponse)
async def update_chapters(
    archive_id: int,
    request: ChaptersUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Update chapters (reorder, rename, delete)."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        chapters_data = [ch.model_dump() for ch in request.chapters]
        archive_editor.update_chapters(archive_path, chapters_data)

        # Sync metadata back to database
        sync_archive_metadata(archive, db)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{archive_id}/archive-cover", response_model=ArchiveResponse)
async def update_archive_cover_in_zip(
    archive_id: int,
    cover_file: UploadFile = File(...),
    crop_x: int = Form(0),
    crop_y: int = Form(0),
    crop_width: int = Form(0),
    crop_height: int = Form(0),
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Replace the cover image inside the archive ZIP file."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        image_data = await cover_file.read()

        crop_data = None
        if crop_width > 0 and crop_height > 0:
            crop_data = {
                "x": crop_x,
                "y": crop_y,
                "width": crop_width,
                "height": crop_height,
            }

        archive_editor.replace_cover_in_archive(archive_path, image_data, crop_data)

        # Also update the thumbnail in the database
        metadata = storage.extract_archive_metadata(archive_path)
        if metadata.get("cover_data"):
            if archive.cover_path:
                storage.delete_cover(archive.cover_path)
            cover_filename = await storage.save_cover_from_bytes(metadata["cover_data"])
            archive.cover_path = cover_filename

        # Update file size
        archive.file_size = os.path.getsize(archive_path)

        db.commit()
        db.refresh(archive)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{archive_id}/chapters/{chapter_key}/icon")
async def get_chapter_icon(
    archive_id: int,
    chapter_key: str,
    db: Session = Depends(get_db),
):
    """Get a chapter's icon image."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        icon_data = archive_editor.get_chapter_icon(archive_path, chapter_key)
        if not icon_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Icon not found")

        return Response(content=icon_data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{archive_id}/chapters/{chapter_key}/icon", response_model=ArchiveResponse)
async def update_chapter_icon(
    archive_id: int,
    chapter_key: str,
    icon_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Replace a chapter's icon."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        image_data = await icon_file.read()
        archive_editor.replace_chapter_icon_in_archive(archive_path, chapter_key, image_data)

        # Update file size
        archive.file_size = os.path.getsize(archive_path)
        db.commit()
        db.refresh(archive)

        # Re-sync metadata
        sync_archive_metadata(archive, db)

        return archive_to_response(archive)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Error replacing chapter icon")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{archive_id}/chapters/{chapter_key}/waveform", response_model=WaveformResponse)
async def get_chapter_waveform(
    archive_id: int,
    chapter_key: str,
    samples: int = 800,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Get waveform data for a chapter's audio."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    editor = None
    try:
        result = archive_editor.get_chapter_audio_path_from_archive(archive_path, chapter_key)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

        temp_dir, audio_path, editor = result

        duration_ms = audio_processor.get_audio_duration(audio_path)
        waveform_samples = audio_processor.get_waveform_data(audio_path, samples)

        return WaveformResponse(duration_ms=duration_ms, samples=waveform_samples)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        if editor:
            editor.cleanup()


@router.get("/{archive_id}/chapters/{chapter_key}/audio")
async def get_chapter_audio(
    archive_id: int,
    chapter_key: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Stream a chapter's audio for preview."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        result = archive_editor.get_chapter_audio_path_from_archive(archive_path, chapter_key)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

        temp_dir, audio_path, editor = result

        # Read audio file into memory then cleanup
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        editor.cleanup()

        # Determine content type based on file extension
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


@router.post("/{archive_id}/chapters/{chapter_key}/split", response_model=ArchiveResponse)
async def split_chapter(
    archive_id: int,
    chapter_key: str,
    request: SplitRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Split a chapter at specific timestamps."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        with archive_editor.ArchiveEditor(archive_path) as editor:
            card_data = editor.read_card_data()
            chapters = card_data.get("content", {}).get("chapters", [])

            # Find the chapter to split
            chapter_idx = None
            chapter = None
            for i, ch in enumerate(chapters):
                if ch.get("key") == chapter_key:
                    chapter_idx = i
                    chapter = ch
                    break

            if chapter is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

            # Get audio file
            audio_file = chapter.get("tracks", [{}])[0].get("file")
            if not audio_file:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter has no audio")

            audio_path = editor.get_chapter_audio_path(audio_file)
            if not audio_path:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

            # Split the audio
            split_dir = tempfile.mkdtemp(prefix="yoto_split_")
            try:
                segment_files = audio_processor.split_audio(
                    audio_path, request.split_points, split_dir
                )

                # Create new chapters from segments
                new_chapters = []
                base_title = chapter.get("title", "Chapter")

                for i, segment_file in enumerate(segment_files):
                    # Generate new key
                    import uuid
                    new_key = f"{chapter_key}_{i}" if i > 0 else chapter_key

                    # Copy segment to audio folder
                    ext = os.path.splitext(audio_file)[1]
                    new_audio_filename = f"{new_key}{ext}"
                    new_audio_path = os.path.join(editor.get_audio_path(), new_audio_filename)
                    shutil.copy(segment_file, new_audio_path)

                    # Get duration of new segment
                    duration_ms = audio_processor.get_audio_duration(new_audio_path)

                    # Create new chapter entry
                    new_chapter = {
                        "key": new_key,
                        "title": f"{base_title} (Part {i + 1})" if len(segment_files) > 1 else base_title,
                        "duration": duration_ms,
                        "tracks": [{"file": new_audio_filename}],
                    }

                    # Copy other properties from original
                    if chapter.get("overlayLabel"):
                        new_chapter["overlayLabel"] = chapter["overlayLabel"]
                    if chapter.get("display"):
                        new_chapter["display"] = chapter["display"].copy()

                    new_chapters.append(new_chapter)

                # Remove original audio file if it's different from the first segment
                if audio_path != new_audio_path:
                    os.remove(audio_path)

                # Replace original chapter with new chapters
                chapters = chapters[:chapter_idx] + new_chapters + chapters[chapter_idx + 1:]
                card_data["content"]["chapters"] = chapters

                # Update total duration
                total_duration = sum(ch.get("duration", 0) for ch in chapters)
                if "metadata" in card_data and "media" in card_data["metadata"]:
                    card_data["metadata"]["media"]["duration"] = total_duration

                editor.write_card_data(card_data)
                editor.save()

            finally:
                shutil.rmtree(split_dir, ignore_errors=True)

        # Sync metadata
        sync_archive_metadata(archive, db)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{archive_id}/chapters/{chapter_key}/trim", response_model=ArchiveResponse)
async def trim_chapter(
    archive_id: int,
    chapter_key: str,
    request: TrimRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Trim a chapter's audio (keep or delete selection)."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        with archive_editor.ArchiveEditor(archive_path) as editor:
            card_data = editor.read_card_data()
            chapters = card_data.get("content", {}).get("chapters", [])

            # Find the chapter
            chapter = next((ch for ch in chapters if ch.get("key") == chapter_key), None)
            if not chapter:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

            # Get audio file
            audio_file = chapter.get("tracks", [{}])[0].get("file")
            if not audio_file:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter has no audio")

            audio_path = editor.get_chapter_audio_path(audio_file)
            if not audio_path:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

            # Trim the audio
            trimmed_path = audio_processor.trim_audio(
                audio_path,
                request.start_ms,
                request.end_ms,
                request.mode
            )

            # Replace original with trimmed
            shutil.move(trimmed_path, audio_path)

            # Update duration
            new_duration = audio_processor.get_audio_duration(audio_path)
            chapter["duration"] = new_duration

            # Update total duration
            total_duration = sum(ch.get("duration", 0) for ch in chapters)
            if "metadata" in card_data and "media" in card_data["metadata"]:
                card_data["metadata"]["media"]["duration"] = total_duration

            editor.write_card_data(card_data)
            editor.save()

        # Sync metadata
        sync_archive_metadata(archive, db)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{archive_id}/chapters/merge", response_model=ArchiveResponse)
async def merge_chapters(
    archive_id: int,
    request: MergeRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Merge multiple chapters into one."""
    if len(request.chapter_keys) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 2 chapters required")

    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        with archive_editor.ArchiveEditor(archive_path) as editor:
            card_data = editor.read_card_data()
            chapters = card_data.get("content", {}).get("chapters", [])

            # Find chapters to merge (in order)
            chapters_to_merge = []
            chapter_indices = []
            for key in request.chapter_keys:
                for i, ch in enumerate(chapters):
                    if ch.get("key") == key:
                        chapters_to_merge.append(ch)
                        chapter_indices.append(i)
                        break

            if len(chapters_to_merge) != len(request.chapter_keys):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some chapters not found")

            # Get audio files
            audio_paths = []
            for ch in chapters_to_merge:
                audio_file = ch.get("tracks", [{}])[0].get("file")
                if not audio_file:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Chapter {ch.get('key')} has no audio"
                    )
                audio_path = editor.get_chapter_audio_path(audio_file)
                if not audio_path:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Audio file not found for chapter {ch.get('key')}"
                    )
                audio_paths.append(audio_path)

            # Merge audio files
            first_audio_file = chapters_to_merge[0].get("tracks", [{}])[0].get("file")
            ext = os.path.splitext(first_audio_file)[1]
            merged_filename = f"merged_{request.chapter_keys[0]}{ext}"
            merged_path = os.path.join(editor.get_audio_path(), merged_filename)

            audio_processor.merge_audio(audio_paths, merged_path)

            # Delete old audio files
            for audio_path in audio_paths:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

            # Get merged duration
            merged_duration = audio_processor.get_audio_duration(merged_path)

            # Create merged chapter
            merged_chapter = {
                "key": request.chapter_keys[0],
                "title": request.new_title,
                "duration": merged_duration,
                "tracks": [{"file": merged_filename}],
            }

            # Keep icon from first chapter if exists
            first_chapter = chapters_to_merge[0]
            if first_chapter.get("display"):
                merged_chapter["display"] = first_chapter["display"].copy()

            # Remove old chapters and insert merged one
            first_idx = min(chapter_indices)
            new_chapters = []
            removed_indices = set(chapter_indices)

            for i, ch in enumerate(chapters):
                if i == first_idx:
                    new_chapters.append(merged_chapter)
                elif i not in removed_indices:
                    new_chapters.append(ch)

            card_data["content"]["chapters"] = new_chapters

            # Update total duration
            total_duration = sum(ch.get("duration", 0) for ch in new_chapters)
            if "metadata" in card_data and "media" in card_data["metadata"]:
                card_data["metadata"]["media"]["duration"] = total_duration

            editor.write_card_data(card_data)
            editor.save()

        # Sync metadata
        sync_archive_metadata(archive, db)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{archive_id}/chapters/add", response_model=ArchiveResponse)
async def add_chapter(
    archive_id: int,
    audio_file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Add a new chapter with an audio file to the archive."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        audio_data = await audio_file.read()
        chapter_title = title or os.path.splitext(audio_file.filename)[0]

        archive_editor.add_chapter(
            archive_path,
            audio_data,
            audio_file.filename,
            chapter_title,
        )

        sync_archive_metadata(archive, db)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)
    except Exception as e:
        logger.exception("Error adding chapter")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{archive_id}/chapters/{chapter_key}/audio", response_model=ArchiveResponse)
async def replace_chapter_audio(
    archive_id: int,
    chapter_key: str,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Replace the audio file of a chapter."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        audio_data = await audio_file.read()

        archive_editor.replace_chapter_audio(
            archive_path,
            chapter_key,
            audio_data,
            audio_file.filename,
        )

        sync_archive_metadata(archive, db)
        sync_discord_after_edit(archive)

        return archive_to_response(archive)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Error replacing chapter audio")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{archive_id}/nfo")
async def get_nfo(
    archive_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Get the NFO file content."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        nfo_content = archive_editor.get_nfo(archive_path)
        if nfo_content is None:
            return {"content": None}
        return {"content": nfo_content}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{archive_id}/nfo", response_model=ArchiveResponse)
async def update_nfo(
    archive_id: int,
    request: NfoUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("archives", "modify")),
):
    """Update the NFO file content."""
    archive = db.query(Archive).filter(Archive.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    archive_path = storage.get_archive_path(archive.archive_path)
    if not archive_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found")

    try:
        archive_editor.update_nfo(archive_path, request.content)

        # Update file size
        archive.file_size = os.path.getsize(archive_path)
        db.commit()
        db.refresh(archive)

        return archive_to_response(archive)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
