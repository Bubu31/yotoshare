"""
Archive Editor Service

Provides functionality for editing archives:
- Extract/save archives to/from temporary directories
- Read/write card-data.json
- Update chapters (reorder, rename, delete)
- Replace cover and chapter icons
"""

import logging
import os
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from PIL import Image
from io import BytesIO

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class ArchiveEditor:
    """Context manager for editing archives in a temporary directory."""

    def __init__(self, archive_path: str):
        self.archive_path = archive_path
        self.temp_dir = None
        self.root_folder = None  # The root folder inside the archive (e.g., "MyCard/")

    def __enter__(self):
        self.extract()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def extract(self) -> str:
        """Extract archive to a temporary directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="yoto_edit_")

        with zipfile.ZipFile(self.archive_path, "r") as zf:
            zf.extractall(self.temp_dir)

            # Find the root folder by looking for card-data.json
            namelist = zf.namelist()
            for name in namelist:
                if name.endswith("card-data.json"):
                    # Could be "data/card-data.json" or "MyCard/data/card-data.json"
                    parts = name.split("/")
                    if len(parts) == 2:
                        # Structure: data/card-data.json (no root folder)
                        self.root_folder = None
                    elif len(parts) >= 3:
                        # Structure: MyCard/data/card-data.json
                        self.root_folder = parts[0]
                    break

        return self.temp_dir

    def save(self, output_path: Optional[str] = None) -> str:
        """Save the modified archive back to a zip file."""
        if not self.temp_dir:
            raise ValueError("Archive not extracted")

        target_path = output_path or self.archive_path

        # Create a new zip file
        temp_zip = target_path + ".tmp"
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.temp_dir):
                # Add directory entries (important for MYO Studio compatibility)
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    arcname = os.path.relpath(dir_path, self.temp_dir).replace("\\", "/") + "/"
                    # Create empty directory entry
                    zf.writestr(zipfile.ZipInfo(arcname), "")
                # Add files
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.temp_dir).replace("\\", "/")
                    zf.write(file_path, arcname)

        # Replace the original file
        if os.path.exists(target_path):
            os.remove(target_path)
        shutil.move(temp_zip, target_path)

        return target_path

    def cleanup(self):
        """Remove the temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def get_data_path(self) -> str:
        """Get the path to the data folder."""
        if self.root_folder:
            return os.path.join(self.temp_dir, self.root_folder, "data")
        return os.path.join(self.temp_dir, "data")

    def get_card_data_path(self) -> str:
        """Get the path to card-data.json."""
        return os.path.join(self.get_data_path(), "card-data.json")

    def read_card_data(self) -> Dict[str, Any]:
        """Read and parse card-data.json."""
        card_data_path = self.get_card_data_path()
        if not os.path.exists(card_data_path):
            # Debug: list what we have in temp dir
            logger.debug("card-data.json not found at: %s", card_data_path)
            logger.debug("root_folder: %s", self.root_folder)
            logger.debug("temp_dir contents: %s", os.listdir(self.temp_dir))
            if self.root_folder:
                root_path = os.path.join(self.temp_dir, self.root_folder)
                if os.path.exists(root_path):
                    logger.debug("root folder contents: %s", os.listdir(root_path))
            raise FileNotFoundError(f"card-data.json not found in archive (looked at: {card_data_path})")

        with open(card_data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_card_data(self, data: Dict[str, Any]):
        """Write card-data.json."""
        card_data_path = self.get_card_data_path()
        with open(card_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_cover_path(self) -> Optional[str]:
        """Get the path to the cover image."""
        if self.root_folder:
            base = os.path.join(self.temp_dir, self.root_folder, "cover")
        else:
            base = os.path.join(self.temp_dir, "cover")

        for ext in ["png", "jpg", "jpeg"]:
            path = os.path.join(base, f"cover.{ext}")
            if os.path.exists(path):
                return path
        return None

    def replace_cover(self, image_data: bytes, crop_data: Optional[Dict] = None) -> str:
        """
        Replace the cover image in the archive.

        Args:
            image_data: Raw image bytes
            crop_data: Optional crop data with x, y, width, height

        Returns:
            Path to the new cover file
        """
        if self.root_folder:
            cover_dir = os.path.join(self.temp_dir, self.root_folder, "cover")
        else:
            cover_dir = os.path.join(self.temp_dir, "cover")

        os.makedirs(cover_dir, exist_ok=True)

        # Remove existing cover files
        for ext in ["png", "jpg", "jpeg"]:
            old_cover = os.path.join(cover_dir, f"cover.{ext}")
            if os.path.exists(old_cover):
                os.remove(old_cover)

        # Open and process the image
        image = Image.open(BytesIO(image_data))

        # Apply crop if provided
        if crop_data:
            x = crop_data.get("x", 0)
            y = crop_data.get("y", 0)
            width = crop_data.get("width", image.width)
            height = crop_data.get("height", image.height)
            image = image.crop((x, y, x + width, y + height))

        # Resize to Yoto NFC card standard (638x1011)
        image = image.resize((638, 1011), Image.Resampling.LANCZOS)

        # Convert to RGB if necessary
        if image.mode in ("RGBA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "RGBA":
                background.paste(image, mask=image.split()[3])
            else:
                background.paste(image)
            image = background

        # Save as PNG
        cover_path = os.path.join(cover_dir, "cover.png")
        image.save(cover_path, "PNG")

        return cover_path

    def get_icons_path(self) -> str:
        """Get the path to the icons folder."""
        if self.root_folder:
            return os.path.join(self.temp_dir, self.root_folder, "icons")
        return os.path.join(self.temp_dir, "icons")

    def get_chapter_icon_path(self, icon_filename: str) -> Optional[str]:
        """Get the full path to a chapter icon."""
        icons_dir = self.get_icons_path()
        icon_path = os.path.join(icons_dir, icon_filename)
        if os.path.exists(icon_path):
            return icon_path
        return None

    def replace_chapter_icon(self, icon_filename: str, image_data: bytes) -> str:
        """
        Replace a chapter icon.

        Args:
            icon_filename: The icon filename (e.g., "chapter1.png")
            image_data: Raw image bytes

        Returns:
            Path to the new icon file
        """
        icons_dir = self.get_icons_path()
        os.makedirs(icons_dir, exist_ok=True)

        # Open and process the image
        image = Image.open(BytesIO(image_data))

        # Resize to 16x16
        image = image.resize((16, 16), Image.Resampling.LANCZOS)

        # Convert to RGBA for PNG with transparency support
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Save
        icon_path = os.path.join(icons_dir, icon_filename)
        image.save(icon_path, "PNG")

        return icon_path

    def get_audio_path(self) -> str:
        """Get the path to the audio folder."""
        if self.root_folder:
            return os.path.join(self.temp_dir, self.root_folder, "audio")
        return os.path.join(self.temp_dir, "audio")

    def get_chapter_audio_path(self, audio_filename: str) -> Optional[str]:
        """Get the full path to a chapter audio file."""
        audio_dir = self.get_audio_path()
        audio_path = os.path.join(audio_dir, audio_filename)
        if os.path.exists(audio_path):
            return audio_path
        return None

    def get_nfo_path(self) -> Optional[str]:
        """Get the path to the signature.nfo file."""
        if self.root_folder:
            nfo_path = os.path.join(self.temp_dir, self.root_folder, "signature.nfo")
        else:
            nfo_path = os.path.join(self.temp_dir, "signature.nfo")

        if os.path.exists(nfo_path):
            return nfo_path
        return None

    def read_nfo(self) -> Optional[str]:
        """Read the signature.nfo file."""
        nfo_path = self.get_nfo_path()
        if nfo_path:
            with open(nfo_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        return None

    def write_nfo(self, content: str):
        """Write the signature.nfo file."""
        if self.root_folder:
            nfo_path = os.path.join(self.temp_dir, self.root_folder, "signature.nfo")
        else:
            nfo_path = os.path.join(self.temp_dir, "signature.nfo")

        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(content)


def update_chapters(
    archive_path: str,
    chapters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Update chapters in an archive.

    Args:
        archive_path: Path to the archive file
        chapters: List of chapter updates with keys: key, title, label, order, delete

    Returns:
        Updated card data
    """
    with ArchiveEditor(archive_path) as editor:
        card_data = editor.read_card_data()

        if "content" not in card_data or "chapters" not in card_data["content"]:
            raise ValueError("No chapters found in card data")

        existing_chapters = card_data["content"]["chapters"]

        # Build a map of existing chapters by key
        chapter_map = {ch["key"]: ch for ch in existing_chapters}

        # Process updates
        chapters_to_delete = set()
        chapter_updates = {}

        for update in chapters:
            key = update.get("key")
            if not key or key not in chapter_map:
                continue

            if update.get("delete"):
                chapters_to_delete.add(key)
                # Delete the audio file
                audio_file = chapter_map[key].get("tracks", [{}])[0].get("file")
                if audio_file:
                    audio_path = editor.get_chapter_audio_path(audio_file)
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                # Delete the icon file
                icon_file = chapter_map[key].get("display", {}).get("icon16x16")
                if icon_file:
                    icon_path = editor.get_chapter_icon_path(icon_file)
                    if icon_path and os.path.exists(icon_path):
                        os.remove(icon_path)
            else:
                chapter_updates[key] = update

        # Filter out deleted chapters
        remaining_chapters = [ch for ch in existing_chapters if ch["key"] not in chapters_to_delete]

        # Apply updates
        for ch in remaining_chapters:
            key = ch["key"]
            if key in chapter_updates:
                update = chapter_updates[key]
                if update.get("title") is not None:
                    ch["title"] = update["title"]
                if update.get("label") is not None:
                    ch["overlayLabel"] = update["label"]
                if update.get("order") is not None:
                    ch["_order"] = update["order"]

        # Sort by order if provided
        if any("_order" in ch for ch in remaining_chapters):
            remaining_chapters.sort(key=lambda ch: ch.get("_order", 999))
            # Remove temporary order field
            for ch in remaining_chapters:
                ch.pop("_order", None)

        # Rename audio and icon files to match new order
        _rename_chapter_files(editor, remaining_chapters, chapter_map)

        # Update card data
        card_data["content"]["chapters"] = remaining_chapters

        # Update total duration
        total_duration = sum(ch.get("duration", 0) for ch in remaining_chapters)
        if "metadata" in card_data and "media" in card_data["metadata"]:
            card_data["metadata"]["media"]["duration"] = total_duration

        editor.write_card_data(card_data)
        editor.save()

        return card_data


def _rename_chapter_files(
    editor: ArchiveEditor,
    chapters: List[Dict[str, Any]],
    original_chapter_map: Dict[str, Dict[str, Any]],
):
    """
    Rename audio and icon files to match the new chapter order.
    Files are renamed using format: XX-YY - Title.ext where XX is the new index.

    Args:
        editor: The ArchiveEditor instance
        chapters: List of chapters in new order
        original_chapter_map: Original chapters indexed by key
    """
    audio_dir = editor.get_audio_path()
    icons_dir = editor.get_icons_path()

    # Get existing audio and icon files
    audio_files = []
    icon_files = []

    if os.path.exists(audio_dir):
        audio_files = [f for f in os.listdir(audio_dir)
                       if f.endswith(('.mp3', '.m4a', '.m4b', '.aac', '.wav', '.flac', '.ogg', '.opus', '.wma', '.ape', '.wv', '.mka', '.webm', '.ac3'))]

    if os.path.exists(icons_dir):
        icon_files = [f for f in os.listdir(icons_dir)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Build mapping: chapter_key -> (old_audio_file, old_icon_file)
    key_to_files = {}
    for ch in chapters:
        key = ch.get("key")
        if not key:
            continue

        # Find audio file for this chapter
        audio_file = None
        # First try from card-data
        if ch.get("tracks") and len(ch["tracks"]) > 0:
            track = ch["tracks"][0]
            if track.get("file"):
                audio_file = track["file"]

        # Fallback: match by key prefix
        if not audio_file:
            for f in audio_files:
                if f.startswith(f"{key}-") or f.startswith(f"{key} -"):
                    audio_file = f
                    break

        # Find icon file for this chapter
        icon_file = None
        # First try from card-data
        if ch.get("display") and ch["display"].get("icon16x16"):
            potential = ch["display"]["icon16x16"]
            if not potential.startswith("yoto:") and potential in icon_files:
                icon_file = potential

        # Fallback: match by key prefix
        if not icon_file:
            for f in icon_files:
                if f.startswith(f"{key}-") or f.startswith(f"{key} -"):
                    icon_file = f
                    break

        key_to_files[key] = (audio_file, icon_file)

    # Rename files to new index-based names (use temp names first to avoid conflicts)
    temp_renames = []

    for new_index, ch in enumerate(chapters):
        key = ch.get("key")
        if not key or key not in key_to_files:
            continue

        audio_file, icon_file = key_to_files[key]
        new_prefix = f"{new_index:02d}"
        title = ch.get("title", "Track")
        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]

        # Rename audio file
        if audio_file and os.path.exists(os.path.join(audio_dir, audio_file)):
            ext = os.path.splitext(audio_file)[1]
            new_audio_name = f"{new_prefix}-01 - {safe_title}{ext}"
            temp_name = f"_temp_{new_index}_{audio_file}"
            old_path = os.path.join(audio_dir, audio_file)
            temp_path = os.path.join(audio_dir, temp_name)
            new_path = os.path.join(audio_dir, new_audio_name)

            os.rename(old_path, temp_path)
            temp_renames.append((temp_path, new_path))

            # Update chapter reference
            if ch.get("tracks") and len(ch["tracks"]) > 0:
                ch["tracks"][0]["file"] = new_audio_name

        # Rename icon file
        if icon_file and os.path.exists(os.path.join(icons_dir, icon_file)):
            ext = os.path.splitext(icon_file)[1]
            new_icon_name = f"{new_prefix}-01 - {safe_title}-icon{ext}"
            temp_name = f"_temp_{new_index}_{icon_file}"
            old_path = os.path.join(icons_dir, icon_file)
            temp_path = os.path.join(icons_dir, temp_name)
            new_path = os.path.join(icons_dir, new_icon_name)

            os.rename(old_path, temp_path)
            temp_renames.append((temp_path, new_path))

            # Update chapter reference
            if "display" not in ch:
                ch["display"] = {}
            ch["display"]["icon16x16"] = new_icon_name

        # Update chapter key to new index
        ch["key"] = new_prefix

    # Complete the renames from temp to final names
    for temp_path, new_path in temp_renames:
        if os.path.exists(temp_path):
            os.rename(temp_path, new_path)


def get_archive_content(archive_path: str) -> Dict[str, Any]:
    """
    Get detailed content of an archive including chapters with audio info.

    Args:
        archive_path: Path to the archive file

    Returns:
        Dict with chapters, cover info, and nfo content
    """
    with ArchiveEditor(archive_path) as editor:
        card_data = editor.read_card_data()

        # Get list of actual audio files in the archive
        audio_files = []
        audio_path = editor.get_audio_path()
        if os.path.exists(audio_path):
            audio_files = sorted([f for f in os.listdir(audio_path) if f.endswith(('.mp3', '.m4a', '.m4b', '.aac', '.wav', '.flac', '.ogg', '.opus', '.wma', '.ape', '.wv', '.mka', '.webm', '.ac3'))])

        chapters = []
        if "content" in card_data and "chapters" in card_data["content"]:
            for i, ch in enumerate(card_data["content"]["chapters"]):
                # Get audio file info - try multiple formats
                audio_file = None
                if ch.get("tracks") and len(ch["tracks"]) > 0:
                    track = ch["tracks"][0]
                    # Check if it's a local file reference
                    if track.get("file"):
                        audio_file = track["file"]
                    elif track.get("trackUrl") and not track["trackUrl"].startswith("yoto:"):
                        audio_file = track["trackUrl"]

                # Fallback: match by index to audio files in folder
                if not audio_file and i < len(audio_files):
                    audio_file = audio_files[i]

                # Get icon file (only if it actually exists as a real file)
                icon_file = None
                chapter_key = ch.get("key")
                if ch.get("display"):
                    potential_icon = ch["display"].get("icon16x16")
                    # Skip yoto:# URLs, only use local files
                    if potential_icon and not potential_icon.startswith("yoto:"):
                        if editor.get_chapter_icon_path(potential_icon):
                            icon_file = potential_icon

                # Try to find icon by chapter_key prefix in icons folder
                if not icon_file and chapter_key:
                    icons_dir = editor.get_icons_path()
                    if os.path.exists(icons_dir):
                        for f in os.listdir(icons_dir):
                            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                                if f.startswith(f"{chapter_key}-") or f.startswith(f"{chapter_key} -"):
                                    icon_file = f
                                    break

                # Duration: convert to milliseconds if it looks like seconds
                duration = ch.get("duration")
                if duration and duration < 100000:  # Likely seconds, not ms
                    duration = duration * 1000

                chapters.append({
                    "key": ch.get("key"),
                    "title": ch.get("title"),
                    "label": ch.get("overlayLabel"),
                    "duration": duration,
                    "audio_file": audio_file,
                    "icon_file": icon_file,
                    "order": i,
                })

        # Check for NFO
        nfo_content = editor.read_nfo()

        return {
            "title": card_data.get("title"),
            "chapters": chapters,
            "has_cover": editor.get_cover_path() is not None,
            "nfo": nfo_content,
        }


def replace_cover_in_archive(
    archive_path: str,
    image_data: bytes,
    crop_data: Optional[Dict] = None,
) -> bool:
    """
    Replace the cover image in an archive.

    Args:
        archive_path: Path to the archive file
        image_data: Raw image bytes
        crop_data: Optional crop data with x, y, width, height

    Returns:
        True if successful
    """
    with ArchiveEditor(archive_path) as editor:
        editor.replace_cover(image_data, crop_data)
        editor.save()
        return True


def replace_chapter_icon_in_archive(
    archive_path: str,
    chapter_key: str,
    image_data: bytes,
) -> bool:
    """
    Replace a chapter icon in an archive.

    Args:
        archive_path: Path to the archive file
        chapter_key: The chapter key
        image_data: Raw image bytes

    Returns:
        True if successful
    """
    with ArchiveEditor(archive_path) as editor:
        card_data = editor.read_card_data()

        # Find the chapter
        chapters = card_data.get("content", {}).get("chapters", [])
        chapter = next((ch for ch in chapters if ch.get("key") == chapter_key), None)

        if not chapter:
            raise ValueError(f"Chapter not found: {chapter_key}")

        # Get or create icon filename
        # IMPORTANT: Skip yoto:# URLs - they are cloud references, not local files
        existing_icon = chapter.get("display", {}).get("icon16x16", "")
        if existing_icon and not existing_icon.startswith("yoto:"):
            icon_filename = existing_icon
        else:
            # Generate a new local filename
            title = chapter.get("title", "icon")
            # Sanitize title for filename
            safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:30]
            icon_filename = f"{chapter_key}-{safe_title}-icon.png"

        # Update card data with the local icon filename
        if "display" not in chapter:
            chapter["display"] = {}
        chapter["display"]["icon16x16"] = icon_filename
        editor.write_card_data(card_data)

        editor.replace_chapter_icon(icon_filename, image_data)
        editor.save()
        return True


def get_chapter_icon(archive_path: str, chapter_key: str) -> Optional[bytes]:
    """
    Get a chapter icon from an archive.

    Args:
        archive_path: Path to the archive file
        chapter_key: The chapter key

    Returns:
        Icon image bytes or None
    """
    with ArchiveEditor(archive_path) as editor:
        card_data = editor.read_card_data()

        # Find the chapter
        chapters = card_data.get("content", {}).get("chapters", [])
        chapter_index = None
        chapter = None
        for i, ch in enumerate(chapters):
            if ch.get("key") == chapter_key:
                chapter_index = i
                chapter = ch
                break

        if not chapter:
            logger.debug("Chapter %s not found", chapter_key)
            return None

        icon_filename = chapter.get("display", {}).get("icon16x16")
        logger.debug("Chapter %s (index %s), icon from card-data: %s", chapter_key, chapter_index, icon_filename)

        # Skip yoto:# cloud references
        if icon_filename and icon_filename.startswith("yoto:"):
            icon_filename = None

        # Verify the file actually exists, otherwise clear and fall through to search
        if icon_filename and not editor.get_chapter_icon_path(icon_filename):
            logger.debug("Icon file from card-data not found: %s, will search", icon_filename)
            icon_filename = None

        # Try to find icon in icons folder
        if not icon_filename:
            icons_dir = editor.get_icons_path()
            logger.debug("Looking in icons dir: %s, exists: %s", icons_dir, os.path.exists(icons_dir))
            if os.path.exists(icons_dir):
                all_files = os.listdir(icons_dir)
                logger.debug("All files in icons dir: %s...", all_files[:5])
                icon_files = sorted([f for f in all_files
                                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

                # Try to match by chapter_key prefix (e.g., "00" matches "00-01 - Title-icon.png")
                for icon_file in icon_files:
                    if icon_file.startswith(f"{chapter_key}-") or icon_file.startswith(f"{chapter_key} -"):
                        icon_filename = icon_file
                        logger.debug("Matched by key prefix: %s", icon_filename)
                        break

                # Fallback: match by index
                if not icon_filename and chapter_index is not None and chapter_index < len(icon_files):
                    icon_filename = icon_files[chapter_index]
                    logger.debug("Matched by index: %s", icon_filename)

        if not icon_filename:
            logger.debug("No icon filename found for chapter %s", chapter_key)
            return None

        icon_path = editor.get_chapter_icon_path(icon_filename)
        logger.debug("Final icon path: %s", icon_path)
        if not icon_path:
            return None

        with open(icon_path, "rb") as f:
            return f.read()


def get_chapter_audio_path_from_archive(archive_path: str, chapter_key: str) -> Optional[str]:
    """
    Get the path to a chapter's audio file by extracting the archive temporarily.

    Note: This returns a path inside a temporary directory. The caller should
    use this path immediately before the archive editor context is closed.

    Args:
        archive_path: Path to the archive file
        chapter_key: The chapter key

    Returns:
        Tuple of (temp_dir, audio_path, editor) or None
    """
    # This is a special case - we need to keep the temp dir alive
    # The caller is responsible for cleanup
    editor = ArchiveEditor(archive_path)
    editor.extract()

    try:
        card_data = editor.read_card_data()
        chapters = card_data.get("content", {}).get("chapters", [])

        # Find chapter index by key
        chapter_index = None
        for i, ch in enumerate(chapters):
            if ch.get("key") == chapter_key:
                chapter_index = i
                break

        if chapter_index is None:
            editor.cleanup()
            return None

        chapter = chapters[chapter_index]

        # Try to get audio file from card-data
        audio_file = None
        if chapter.get("tracks") and len(chapter["tracks"]) > 0:
            track = chapter["tracks"][0]
            if track.get("file"):
                audio_file = track["file"]
            elif track.get("trackUrl") and not track["trackUrl"].startswith("yoto:"):
                audio_file = track["trackUrl"]

        # If no file in card-data, scan the audio folder and match by index
        if not audio_file:
            audio_dir = editor.get_audio_path()
            if os.path.exists(audio_dir):
                audio_files = sorted([f for f in os.listdir(audio_dir)
                                     if f.endswith(('.mp3', '.m4a', '.m4b', '.aac', '.wav', '.flac', '.ogg', '.opus', '.wma', '.ape', '.wv', '.mka', '.webm', '.ac3'))])
                if chapter_index < len(audio_files):
                    audio_file = audio_files[chapter_index]

        if not audio_file:
            editor.cleanup()
            return None

        audio_path = editor.get_chapter_audio_path(audio_file)
        if not audio_path:
            editor.cleanup()
            return None

        return (editor.temp_dir, audio_path, editor)
    except Exception as e:
        logger.error("Error getting audio path: %s", e)
        editor.cleanup()
        return None


def add_chapter(
    archive_path: str,
    audio_data: bytes,
    audio_filename: str,
    title: str,
) -> Dict[str, Any]:
    """
    Add a new chapter with an audio file to an archive.

    Args:
        archive_path: Path to the archive file
        audio_data: Raw audio file bytes
        audio_filename: Original filename of the audio (for extension)
        title: Chapter title

    Returns:
        Updated card data
    """
    from app.services.audio_processor import get_audio_duration, convert_to_mp3, is_mp3

    with ArchiveEditor(archive_path) as editor:
        card_data = editor.read_card_data()

        if "content" not in card_data:
            card_data["content"] = {}
        if "chapters" not in card_data["content"]:
            card_data["content"]["chapters"] = []

        chapters = card_data["content"]["chapters"]

        # Determine next key (max existing key + 1, zero-padded)
        existing_keys = []
        for ch in chapters:
            try:
                existing_keys.append(int(ch.get("key", "0")))
            except (ValueError, TypeError):
                pass
        next_key = max(existing_keys, default=-1) + 1
        new_key = f"{next_key:02d}"

        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]

        # Write audio file to archive (temp name first)
        audio_dir = editor.get_audio_path()
        os.makedirs(audio_dir, exist_ok=True)

        orig_ext = os.path.splitext(audio_filename)[1] or ".mp3"
        tmp_audio_path = os.path.join(audio_dir, f"_tmp_{new_key}{orig_ext}")
        with open(tmp_audio_path, "wb") as f:
            f.write(audio_data)

        # Convert to MP3 if needed
        if not is_mp3(audio_filename):
            new_audio_name = f"{new_key}-01 - {safe_title}.mp3"
            audio_path = os.path.join(audio_dir, new_audio_name)
            convert_to_mp3(tmp_audio_path, audio_path)
            os.remove(tmp_audio_path)
        else:
            new_audio_name = f"{new_key}-01 - {safe_title}.mp3"
            audio_path = os.path.join(audio_dir, new_audio_name)
            os.rename(tmp_audio_path, audio_path)

        # Get duration
        duration_ms = get_audio_duration(audio_path)

        # Create new chapter entry
        new_chapter = {
            "key": new_key,
            "title": title,
            "duration": duration_ms,
            "tracks": [{"file": new_audio_name}],
            "display": {},
        }
        chapters.append(new_chapter)

        # Update total duration
        total_duration = sum(ch.get("duration", 0) for ch in chapters)
        if "metadata" not in card_data:
            card_data["metadata"] = {"media": {}}
        if "media" not in card_data["metadata"]:
            card_data["metadata"]["media"] = {}
        card_data["metadata"]["media"]["duration"] = total_duration

        editor.write_card_data(card_data)
        editor.save()

        return card_data


def replace_chapter_audio(
    archive_path: str,
    chapter_key: str,
    audio_data: bytes,
    audio_filename: str,
) -> Dict[str, Any]:
    """
    Replace the audio file of an existing chapter.

    Args:
        archive_path: Path to the archive file
        chapter_key: The chapter key
        audio_data: Raw audio file bytes
        audio_filename: Original filename (for extension)

    Returns:
        Updated card data
    """
    from app.services.audio_processor import get_audio_duration, convert_to_mp3, is_mp3

    with ArchiveEditor(archive_path) as editor:
        card_data = editor.read_card_data()
        chapters = card_data.get("content", {}).get("chapters", [])

        chapter = next((ch for ch in chapters if ch.get("key") == chapter_key), None)
        if not chapter:
            raise ValueError(f"Chapter not found: {chapter_key}")

        # Delete old audio file
        old_audio = chapter.get("tracks", [{}])[0].get("file")
        if old_audio:
            old_path = editor.get_chapter_audio_path(old_audio)
            if old_path and os.path.exists(old_path):
                os.remove(old_path)

        # Write new audio file
        title = chapter.get("title", "Track")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]

        audio_dir = editor.get_audio_path()
        os.makedirs(audio_dir, exist_ok=True)

        orig_ext = os.path.splitext(audio_filename)[1] or ".mp3"
        tmp_audio_path = os.path.join(audio_dir, f"_tmp_{chapter_key}{orig_ext}")
        with open(tmp_audio_path, "wb") as f:
            f.write(audio_data)

        # Convert to MP3 if needed
        new_audio_name = f"{chapter_key}-01 - {safe_title}.mp3"
        audio_path = os.path.join(audio_dir, new_audio_name)
        if not is_mp3(audio_filename):
            convert_to_mp3(tmp_audio_path, audio_path)
            os.remove(tmp_audio_path)
        else:
            os.rename(tmp_audio_path, audio_path)

        # Update duration
        duration_ms = get_audio_duration(audio_path)
        chapter["duration"] = duration_ms

        # Update track reference
        if not chapter.get("tracks"):
            chapter["tracks"] = [{}]
        chapter["tracks"][0]["file"] = new_audio_name

        # Update total duration
        total_duration = sum(ch.get("duration", 0) for ch in chapters)
        if "metadata" in card_data and "media" in card_data["metadata"]:
            card_data["metadata"]["media"]["duration"] = total_duration

        editor.write_card_data(card_data)
        editor.save()

        return card_data


def update_nfo(archive_path: str, content: str) -> bool:
    """
    Update the NFO file in an archive.

    Args:
        archive_path: Path to the archive file
        content: New NFO content

    Returns:
        True if successful
    """
    with ArchiveEditor(archive_path) as editor:
        editor.write_nfo(content)
        editor.save()
        return True


def get_nfo(archive_path: str) -> Optional[str]:
    """
    Get the NFO content from an archive.

    Args:
        archive_path: Path to the archive file

    Returns:
        NFO content or None
    """
    with ArchiveEditor(archive_path) as editor:
        return editor.read_nfo()
