import logging
import os
import uuid
import json
import zipfile
import tempfile
import aiofiles
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO
from fastapi import UploadFile
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def ensure_directories():
    os.makedirs(settings.archives_path, exist_ok=True)
    os.makedirs(settings.covers_path, exist_ok=True)


async def save_archive(file: UploadFile) -> tuple[str, int]:
    ensure_directories()
    file_ext = Path(file.filename).suffix or ".zip"
    filename = f"{uuid.uuid4()}{file_ext}"
    filepath = os.path.join(settings.archives_path, filename)

    file_size = 0
    async with aiofiles.open(filepath, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)
            file_size += len(chunk)

    return filename, file_size


async def save_cover(file: UploadFile, max_size: tuple[int, int] = (400, 600)) -> Optional[str]:
    if not file:
        return None

    ensure_directories()
    content = await file.read()

    try:
        image = Image.open(BytesIO(content))
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(settings.covers_path, filename)
        image.save(filepath, "JPEG", quality=85)

        return filename
    except Exception:
        return None


def delete_archive(filename: str) -> bool:
    filepath = os.path.join(settings.archives_path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def delete_cover(filename: str) -> bool:
    if not filename:
        return True
    filepath = os.path.join(settings.covers_path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def get_archive_path(filename: str) -> Optional[str]:
    filepath = os.path.join(settings.archives_path, filename)
    logger.debug("Looking for archive: %s", filepath)
    logger.debug("Archives directory: %s (exists: %s)", settings.archives_path, os.path.exists(settings.archives_path))
    if os.path.exists(settings.archives_path):
        try:
            files = os.listdir(settings.archives_path)
            logger.debug("Files in directory (%d): %s...", len(files), files[:10])
        except Exception as e:
            logger.error("Error listing directory: %s", e)
    if os.path.exists(filepath):
        logger.debug("File found: %s", filepath)
        return filepath
    logger.warning("File NOT found: %s", filepath)
    return None


def get_cover_path(filename: str) -> Optional[str]:
    if not filename:
        return None
    filepath = os.path.join(settings.covers_path, filename)
    if os.path.exists(filepath):
        return filepath
    return None


def extract_archive_metadata(archive_path: str) -> dict:
    """Extract metadata from archive: title, chapters, duration from card-data.json, cover from cover/cover.png"""
    metadata = {
        "title": None,
        "cover_data": None,
        "total_duration": None,
        "chapters_count": None,
        "chapters": None,
    }

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = zf.namelist()

            # Look for card-data.json
            card_data_paths = [n for n in namelist if n.endswith("data/card-data.json")]
            if card_data_paths:
                with zf.open(card_data_paths[0]) as f:
                    try:
                        card_data = json.load(f)
                        metadata["title"] = card_data.get("title")

                        # Extract duration from metadata
                        if "metadata" in card_data and "media" in card_data["metadata"]:
                            media = card_data["metadata"]["media"]
                            duration = media.get("duration")
                            if duration is not None:
                                duration = int(duration)
                                if duration < 100000:  # Likely seconds, not ms
                                    duration *= 1000
                            metadata["total_duration"] = duration

                        # Extract chapters
                        if "content" in card_data and "chapters" in card_data["content"]:
                            chapters_raw = card_data["content"]["chapters"]
                            metadata["chapters_count"] = len(chapters_raw)

                            # Extract relevant chapter info
                            chapters = []
                            for ch in chapters_raw:
                                chapter_info = {
                                    "key": ch.get("key"),
                                    "title": ch.get("title"),
                                    "label": ch.get("overlayLabel"),
                                    "duration": ch.get("duration"),
                                    "icon": ch.get("display", {}).get("icon16x16") if ch.get("display") else None,
                                }
                                chapters.append(chapter_info)
                            metadata["chapters"] = chapters

                    except json.JSONDecodeError:
                        pass

            # Look for cover image
            cover_paths = [n for n in namelist if n.endswith("cover/cover.png") or n.endswith("cover/cover.jpg")]
            if cover_paths:
                with zf.open(cover_paths[0]) as f:
                    metadata["cover_data"] = f.read()

    except zipfile.BadZipFile:
        pass

    return metadata


async def save_cover_from_bytes(image_data: bytes, max_size: tuple[int, int] = (400, 600)) -> Optional[str]:
    """Save cover image from raw bytes"""
    if not image_data:
        return None

    ensure_directories()

    try:
        image = Image.open(BytesIO(image_data))
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(settings.covers_path, filename)
        image.save(filepath, "JPEG", quality=85)

        return filename
    except Exception:
        return None
