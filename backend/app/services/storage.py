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


def extract_submission_data(archive_path: str, archive_filename: str) -> Optional[str]:
    """Extract submission ZIP contents to a flat directory for fast access.

    Creates: submissions-data/{uuid}/
        card-data.json, cover.jpg/.png, icons/{key}.ext, audio/{key}.ext
    Returns the extraction directory path, or None on failure.
    """
    stem = Path(archive_filename).stem
    dest = os.path.join(settings.submissions_data_path, stem)
    os.makedirs(dest, exist_ok=True)
    icons_dir = os.path.join(dest, "icons")
    audio_dir = os.path.join(dest, "audio")
    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = zf.namelist()

            # --- card-data.json ---
            card_data_paths = [n for n in namelist if n.endswith("data/card-data.json")]
            card_data = None
            if card_data_paths:
                with zf.open(card_data_paths[0]) as f:
                    card_data = json.load(f)
                with open(os.path.join(dest, "card-data.json"), "w", encoding="utf-8") as out:
                    json.dump(card_data, out, ensure_ascii=False)

            # --- cover ---
            cover_entries = [n for n in namelist if n.endswith("cover/cover.png") or n.endswith("cover/cover.jpg")]
            if cover_entries:
                ext = ".png" if cover_entries[0].lower().endswith(".png") else ".jpg"
                with zf.open(cover_entries[0]) as src, open(os.path.join(dest, f"cover{ext}"), "wb") as out:
                    out.write(src.read())

            if not card_data:
                return dest

            chapters = card_data.get("content", {}).get("chapters", [])

            # --- collect audio files from the archive ---
            audio_extensions = ('.mp3', '.m4a', '.m4b', '.aac', '.wav', '.flac', '.ogg', '.opus')
            audio_entries = sorted([
                n for n in namelist
                if "audio/" in n and not n.endswith("/") and n.lower().endswith(audio_extensions)
            ])

            # --- collect icon files from the archive ---
            icon_entries = sorted([n for n in namelist if ("icons/" in n) and n.lower().endswith((".png", ".jpg", ".jpeg"))])

            # --- extract per chapter ---
            for i, ch in enumerate(chapters):
                key = ch.get("key", f"chapter_{i}")

                # Audio: try card-data reference first, then index fallback
                audio_file_in_zip = None
                if ch.get("tracks") and len(ch["tracks"]) > 0:
                    track = ch["tracks"][0]
                    ref = track.get("file") or (track.get("trackUrl") if track.get("trackUrl") and not track["trackUrl"].startswith("yoto:") else None)
                    if ref:
                        for ae in audio_entries:
                            if ae.endswith(f"/{ref}") or ae.endswith(f"\\{ref}"):
                                audio_file_in_zip = ae
                                break
                if not audio_file_in_zip and i < len(audio_entries):
                    audio_file_in_zip = audio_entries[i]

                if audio_file_in_zip:
                    ext = os.path.splitext(audio_file_in_zip)[1]
                    with zf.open(audio_file_in_zip) as src, open(os.path.join(audio_dir, f"{key}{ext}"), "wb") as out:
                        out.write(src.read())

                # Icon: try card-data reference, then key prefix, then index fallback
                icon_file_in_zip = None
                icon_filename = ch.get("display", {}).get("icon16x16") if ch.get("display") else None
                if icon_filename and not icon_filename.startswith("yoto:"):
                    for ie in icon_entries:
                        if ie.endswith(f"/{icon_filename}") or ie.endswith(f"\\{icon_filename}"):
                            icon_file_in_zip = ie
                            break
                if not icon_file_in_zip:
                    for ie in icon_entries:
                        basename = ie.split("/")[-1]
                        if basename.startswith(f"{key}-") or basename.startswith(f"{key} -"):
                            icon_file_in_zip = ie
                            break
                if not icon_file_in_zip and i < len(icon_entries):
                    icon_file_in_zip = icon_entries[i]

                if icon_file_in_zip:
                    ext = os.path.splitext(icon_file_in_zip)[1]
                    with zf.open(icon_file_in_zip) as src, open(os.path.join(icons_dir, f"{key}{ext}"), "wb") as out:
                        out.write(src.read())

        return dest
    except Exception:
        logger.exception("Failed to extract submission data for %s", archive_filename)
        return None


def get_submission_data_dir(archive_filename: str) -> Optional[str]:
    """Return the path to the extracted submission data directory, or None."""
    stem = Path(archive_filename).stem
    dirpath = os.path.join(settings.submissions_data_path, stem)
    if os.path.isdir(dirpath):
        return dirpath
    return None


def delete_submission_data(archive_filename: str) -> bool:
    """Delete the extracted submission data directory."""
    import shutil
    dirpath = get_submission_data_dir(archive_filename)
    if dirpath and os.path.isdir(dirpath):
        shutil.rmtree(dirpath, ignore_errors=True)
        return True
    return False


def extract_archive_data(archive_path: str, archive_filename: str) -> Optional[str]:
    """Extract archive ZIP to a flat directory for fast access (on-demand cache).

    Creates: archives-data/{uuid}/
        card-data.json, cover.jpg/.png, icons/{key}.ext, audio/{key}.ext, .nfo (if any)
    Returns the extraction directory path, or None on failure.
    """
    import shutil
    stem = Path(archive_filename).stem
    dest = os.path.join(settings.archives_data_path, stem)
    os.makedirs(dest, exist_ok=True)
    icons_dir = os.path.join(dest, "icons")
    audio_dir = os.path.join(dest, "audio")
    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = zf.namelist()

            # card-data.json
            card_data_paths = [n for n in namelist if n.endswith("data/card-data.json")]
            card_data = None
            if card_data_paths:
                with zf.open(card_data_paths[0]) as f:
                    card_data = json.load(f)
                with open(os.path.join(dest, "card-data.json"), "w", encoding="utf-8") as out:
                    json.dump(card_data, out, ensure_ascii=False)

            # cover
            cover_entries = [n for n in namelist if n.endswith("cover/cover.png") or n.endswith("cover/cover.jpg")]
            if cover_entries:
                ext = ".png" if cover_entries[0].lower().endswith(".png") else ".jpg"
                with zf.open(cover_entries[0]) as src, open(os.path.join(dest, f"cover{ext}"), "wb") as out:
                    out.write(src.read())

            # nfo
            nfo_entries = [n for n in namelist if n.lower().endswith(".nfo")]
            if nfo_entries:
                with zf.open(nfo_entries[0]) as src, open(os.path.join(dest, "info.nfo"), "wb") as out:
                    out.write(src.read())

            if not card_data:
                return dest

            chapters = card_data.get("content", {}).get("chapters", [])
            audio_extensions = ('.mp3', '.m4a', '.m4b', '.aac', '.wav', '.flac', '.ogg', '.opus')
            audio_entries = sorted([
                n for n in namelist
                if "audio/" in n and not n.endswith("/") and n.lower().endswith(audio_extensions)
            ])
            icon_entries = sorted([
                n for n in namelist
                if "icons/" in n and n.lower().endswith((".png", ".jpg", ".jpeg"))
            ])

            for i, ch in enumerate(chapters):
                key = ch.get("key", f"chapter_{i}")

                # Audio
                audio_file_in_zip = None
                if ch.get("tracks") and len(ch["tracks"]) > 0:
                    track = ch["tracks"][0]
                    ref = track.get("file") or (
                        track.get("trackUrl") if track.get("trackUrl") and not track["trackUrl"].startswith("yoto:") else None
                    )
                    if ref:
                        for ae in audio_entries:
                            if ae.endswith(f"/{ref}") or ae.endswith(f"\\{ref}"):
                                audio_file_in_zip = ae
                                break
                if not audio_file_in_zip and i < len(audio_entries):
                    audio_file_in_zip = audio_entries[i]

                if audio_file_in_zip:
                    ext = os.path.splitext(audio_file_in_zip)[1]
                    with zf.open(audio_file_in_zip) as src, open(os.path.join(audio_dir, f"{key}{ext}"), "wb") as out:
                        out.write(src.read())

                # Icon
                icon_file_in_zip = None
                icon_filename = ch.get("display", {}).get("icon16x16") if ch.get("display") else None
                if icon_filename and not icon_filename.startswith("yoto:"):
                    for ie in icon_entries:
                        if ie.endswith(f"/{icon_filename}") or ie.endswith(f"\\{icon_filename}"):
                            icon_file_in_zip = ie
                            break
                if not icon_file_in_zip:
                    for ie in icon_entries:
                        basename = ie.split("/")[-1]
                        if basename.startswith(f"{key}-") or basename.startswith(f"{key} -"):
                            icon_file_in_zip = ie
                            break
                if not icon_file_in_zip and i < len(icon_entries):
                    icon_file_in_zip = icon_entries[i]

                if icon_file_in_zip:
                    ext = os.path.splitext(icon_file_in_zip)[1]
                    with zf.open(icon_file_in_zip) as src, open(os.path.join(icons_dir, f"{key}{ext}"), "wb") as out:
                        out.write(src.read())

        # Touch last-access file for GC TTL
        open(os.path.join(dest, ".last_access"), "w").close()
        return dest
    except Exception:
        logger.exception("Failed to extract archive data for %s", archive_filename)
        return None


def get_archive_data_dir(archive_filename: str) -> Optional[str]:
    """Return path to extracted archive data dir, or None. Refreshes TTL on access."""
    stem = Path(archive_filename).stem
    dirpath = os.path.join(settings.archives_data_path, stem)
    if os.path.isdir(dirpath):
        # Refresh TTL
        open(os.path.join(dirpath, ".last_access"), "w").close()
        return dirpath
    return None


def delete_archive_data(archive_filename: str) -> bool:
    """Delete extracted archive data directory (call after editing the ZIP)."""
    import shutil
    stem = Path(archive_filename).stem
    dirpath = os.path.join(settings.archives_data_path, stem)
    if os.path.isdir(dirpath):
        shutil.rmtree(dirpath, ignore_errors=True)
        return True
    return False


def cleanup_old_archive_data(max_age_seconds: int = 1800) -> int:
    """GC: delete extracted archive data dirs not accessed for more than max_age_seconds.
    Returns the number of directories deleted."""
    import shutil
    import time
    base = settings.archives_data_path
    if not os.path.isdir(base):
        return 0
    now = time.time()
    count = 0
    for entry in os.scandir(base):
        if not entry.is_dir():
            continue
        touch_path = os.path.join(entry.path, ".last_access")
        ref_path = touch_path if os.path.exists(touch_path) else entry.path
        try:
            if now - os.path.getmtime(ref_path) > max_age_seconds:
                shutil.rmtree(entry.path, ignore_errors=True)
                count += 1
        except OSError:
            pass
    return count


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
