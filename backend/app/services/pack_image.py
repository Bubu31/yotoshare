"""Generate composite OG images for share packs."""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings
from app.services.storage import get_cover_path

logger = logging.getLogger(__name__)
settings = get_settings()

# Fallback dimensions (when no template)
FALLBACK_W = 1086
FALLBACK_H = 913

# Title position ratio (just below #JEPARTAGE)
TITLE_Y_RATIO = 0.115

COVERS_GAP = 8
COVER_RADIUS = 12
NFC_RATIO = 2 / 3  # width / height for NFC portrait cards
MAX_COVERS = 9

# White detection threshold (R, G, B all above this = "white")
WHITE_THRESHOLD = 240

# Grid layout per cover count: list of items per row
GRID_LAYOUTS = {
    1: [1],
    2: [1, 1],
    3: [2, 1],
    4: [2, 2],
    5: [3, 2],
    6: [2, 2, 2],
    7: [3, 2, 2],
    8: [3, 3, 2],
    9: [3, 3, 3],
}

# Colors (fallback mode only)
TITLE_COLOR = (45, 62, 80)
ACCENT_COLOR = (30, 58, 95)
BG_COLOR_TOP = (230, 240, 250)
BG_COLOR_BOTTOM = (200, 220, 240)

# Font paths
FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
BOLD_FONT_PATH = FONTS_DIR / "NotoSans-Bold.ttf"
REGULAR_FONT_PATH = FONTS_DIR / "NotoSans-Regular.ttf"


def _load_font(bold: bool = False, size: int = 24) -> ImageFont.FreeTypeFont:
    path = BOLD_FONT_PATH if bold else REGULAR_FONT_PATH
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, IOError):
        logger.warning("Font not found at %s, using default", path)
        return ImageFont.load_default()


def _detect_white_rect(img: Image.Image) -> Optional[tuple[int, int, int, int]]:
    """Detect the largest white rectangle in the image.

    Returns (x, y, w, h) or None if not found.
    Scans for contiguous near-white pixels (R,G,B > WHITE_THRESHOLD).
    """
    arr = np.array(img.convert("RGB"))
    # Create binary mask: True where all channels > threshold
    white_mask = np.all(arr > WHITE_THRESHOLD, axis=2)

    if not white_mask.any():
        return None

    # Find rows and cols that contain white pixels
    row_has_white = white_mask.any(axis=1)
    col_has_white = white_mask.any(axis=0)

    # Find the vertical extent of the white region
    white_rows = np.where(row_has_white)[0]
    white_cols = np.where(col_has_white)[0]

    if len(white_rows) == 0 or len(white_cols) == 0:
        return None

    # Find the largest contiguous block of white rows
    # (to avoid picking up scattered white pixels)
    row_groups = []
    start = white_rows[0]
    for i in range(1, len(white_rows)):
        if white_rows[i] - white_rows[i - 1] > 3:  # allow small gaps
            row_groups.append((start, white_rows[i - 1]))
            start = white_rows[i]
    row_groups.append((start, white_rows[-1]))

    # Pick the tallest group
    best_group = max(row_groups, key=lambda g: g[1] - g[0])
    y_min, y_max = best_group

    # Within those rows, find the horizontal extent
    sub_mask = white_mask[y_min:y_max + 1, :]
    col_density = sub_mask.mean(axis=0)
    # Columns where at least 50% of the rows in the group are white
    dense_cols = np.where(col_density > 0.5)[0]

    if len(dense_cols) == 0:
        return None

    x_min = int(dense_cols[0])
    x_max = int(dense_cols[-1])
    y_min = int(y_min)
    y_max = int(y_max)

    w = x_max - x_min
    h = y_max - y_min

    # Sanity check: rectangle should be at least 10% of image in each dimension
    img_w, img_h = img.size
    if w < img_w * 0.1 or h < img_h * 0.1:
        return None

    logger.info("Detected white rectangle: x=%d y=%d w=%d h=%d", x_min, y_min, w, h)
    return (x_min, y_min, w, h)


def _draw_gradient(img: Image.Image):
    """Draw a light vertical gradient fallback background."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / h
        r = int(BG_COLOR_TOP[0] + (BG_COLOR_BOTTOM[0] - BG_COLOR_TOP[0]) * ratio)
        g = int(BG_COLOR_TOP[1] + (BG_COLOR_BOTTOM[1] - BG_COLOR_TOP[1]) * ratio)
        b = int(BG_COLOR_TOP[2] + (BG_COLOR_BOTTOM[2] - BG_COLOR_TOP[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _round_corners(img: Image.Image, radius: int) -> Image.Image:
    """Add rounded corners to an image, returning RGBA."""
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [(0, 0), (img.size[0] - 1, img.size[1] - 1)],
        radius=radius, fill=255,
    )
    result = img.convert("RGBA")
    result.putalpha(mask)
    return result


def _draw_text_centered(draw: ImageDraw.Draw, y: int, text: str, font, fill, canvas_w: int):
    """Draw text centered horizontally. Returns text height."""
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    x = (canvas_w - text_w) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines or [""]


def _compute_grid_positions(
    count: int,
    zone_x: int, zone_y: int,
    zone_w: int, zone_h: int,
    gap: int,
) -> list[tuple[int, int, int, int]]:
    """Compute (x, y, cell_w, cell_h) for each cover in the grid."""
    n = min(count, MAX_COVERS)
    layout = GRID_LAYOUTS.get(n, GRID_LAYOUTS[9])
    num_rows = len(layout)
    max_cols = max(layout)

    # For 5+ covers, size cells as if 3 rows to keep them small enough
    sizing_rows = max(num_rows, 3) if n >= 5 else num_rows

    # Compute cell size: fit NFC ratio within available space
    cell_w_from_cols = (zone_w - gap * (max_cols - 1)) // max_cols
    cell_h_from_rows = (zone_h - gap * (sizing_rows - 1)) // sizing_rows
    cell_h_from_w = int(cell_w_from_cols / NFC_RATIO)
    cell_w_from_h = int(cell_h_from_rows * NFC_RATIO)

    if cell_h_from_w <= cell_h_from_rows:
        cell_w, cell_h = cell_w_from_cols, cell_h_from_w
    else:
        cell_w, cell_h = cell_w_from_h, cell_h_from_rows

    # Center grid vertically
    total_h = num_rows * cell_h + (num_rows - 1) * gap
    start_y = zone_y + (zone_h - total_h) // 2

    positions = []
    for row_idx, row_count in enumerate(layout):
        row_w = row_count * cell_w + (row_count - 1) * gap
        start_x = zone_x + (zone_w - row_w) // 2
        cy = start_y + row_idx * (cell_h + gap)
        for col in range(row_count):
            cx = start_x + col * (cell_w + gap)
            positions.append((cx, cy, cell_w, cell_h))

    return positions


def generate_pack_image(
    pack_name: str,
    cover_filenames: list[str],
    description: Optional[str] = None,
    background_path: Optional[str] = None,
    mascot_path: Optional[str] = None,
) -> Image.Image:
    """Generate image using the template background + dynamic covers."""
    has_template = False
    canvas_w, canvas_h = FALLBACK_W, FALLBACK_H
    white_rect = None

    # === Load template background at its native size ===
    if background_path and os.path.exists(background_path):
        try:
            bg = Image.open(background_path).convert("RGB")
            canvas_w, canvas_h = bg.size
            # Detect the white rectangle before compositing
            white_rect = _detect_white_rect(bg)
            img = Image.new("RGBA", (canvas_w, canvas_h))
            img.paste(bg, (0, 0))
            has_template = True
        except Exception:
            logger.warning("Failed to load template background")
            img = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    else:
        img = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))

    if not has_template:
        _draw_gradient(img)
        draw = ImageDraw.Draw(img)
        tag_font = _load_font(bold=True, size=int(canvas_h * 0.048))
        _draw_text_centered(draw, int(canvas_h * 0.015), "#JEPARTAGE", tag_font, ACCENT_COLOR, canvas_w)
        # Fallback white rect
        fx, fy = int(canvas_w * 0.035), int(canvas_h * 0.155)
        fw, fh = int(canvas_w * 0.40), int(canvas_h * 0.71)
        draw.rounded_rectangle([(fx, fy), (fx + fw, fy + fh)], radius=16, fill=(255, 255, 255, 230))
        white_rect = (fx, fy, fw, fh)

    # === Covers zone: use detected white rectangle with adjustments ===
    if white_rect:
        covers_x, covers_y, covers_w, covers_h = white_rect
        covers_x -= 90   # shift left
        covers_y += 7     # shift down
        covers_h -= 17    # reduce height
    else:
        covers_x = int(canvas_w * 0.035)
        covers_y = int(canvas_h * 0.155)
        covers_w = int(canvas_w * 0.40)
        covers_h = int(canvas_h * 0.71)

    # === Pack name below #JEPARTAGE ===
    draw = ImageDraw.Draw(img)
    title_y = int(canvas_h * TITLE_Y_RATIO) + 45
    font_size = int(canvas_h * 0.042)
    name_font = _load_font(bold=True, size=font_size)
    name_lines = _wrap_text(pack_name, name_font, canvas_w - 80)
    ny = title_y
    for line in name_lines[:2]:
        _draw_text_centered(draw, ny, line, name_font, TITLE_COLOR, canvas_w)
        bbox = name_font.getbbox(line)
        ny += bbox[3] - bbox[1] + 4

    # === Load covers (max 9) ===
    covers = []
    for filename in cover_filenames[:MAX_COVERS]:
        cp = get_cover_path(filename)
        if cp:
            try:
                c = Image.open(cp)
                if c.mode not in ("RGB", "RGBA"):
                    c = c.convert("RGB")
                covers.append(c)
            except Exception:
                continue

    # === Place covers in NFC portrait format ===
    if covers:
        inner_pad = 10
        zone_x = covers_x + inner_pad
        zone_y = covers_y + inner_pad
        zone_w = covers_w - inner_pad * 2
        zone_h = covers_h - inner_pad * 2

        positions = _compute_grid_positions(
            len(covers), zone_x, zone_y, zone_w, zone_h, COVERS_GAP,
        )

        for i, cover in enumerate(covers[:len(positions)]):
            cx, cy, cell_w, cell_h = positions[i]

            cover_copy = cover.copy()
            cover_copy.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)

            paste_x = cx + (cell_w - cover_copy.width) // 2
            paste_y = cy + (cell_h - cover_copy.height) // 2

            rounded = _round_corners(cover_copy, COVER_RADIUS)
            img.paste(rounded, (paste_x, paste_y), mask=rounded)

    # === Mascot (only without template) ===
    if not has_template and mascot_path and os.path.exists(mascot_path):
        try:
            mascot = Image.open(mascot_path).convert("RGBA")
            max_h = int(canvas_h * 0.30)
            if mascot.height > max_h:
                ratio = max_h / mascot.height
                mascot = mascot.resize(
                    (int(mascot.width * ratio), max_h), Image.Resampling.LANCZOS
                )
            mx = canvas_w - mascot.width - 60
            my = canvas_h - mascot.height - 30
            img.paste(mascot, (mx, my), mask=mascot)
        except Exception:
            logger.warning("Failed to load mascot image")

    return img.convert("RGB")


def save_pack_image(
    pack_name: str,
    cover_filenames: list[str],
    description: Optional[str] = None,
    db=None,
) -> Optional[str]:
    """Generate and save a pack image. Returns the filename."""
    try:
        os.makedirs(settings.packs_path, exist_ok=True)

        background_path = None
        mascot_path = None
        if db is not None:
            from app.models import PackAsset
            for asset in db.query(PackAsset).all():
                asset_filepath = os.path.join(settings.pack_assets_path, asset.filename)
                if asset.asset_type == "background":
                    background_path = asset_filepath
                elif asset.asset_type == "mascot":
                    mascot_path = asset_filepath

        img = generate_pack_image(
            pack_name, cover_filenames, description,
            background_path=background_path,
            mascot_path=mascot_path,
        )
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(settings.packs_path, filename)
        img.save(filepath, "JPEG", quality=90)
        logger.info("Saved pack image: %s", filename)
        return filename
    except Exception:
        logger.exception("Error generating pack image")
        return None


def delete_pack_image(filename: str) -> bool:
    """Delete a pack image file."""
    if not filename:
        return True
    filepath = os.path.join(settings.packs_path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def get_pack_image_path(filename: str) -> Optional[str]:
    """Get full path to a pack image."""
    if not filename:
        return None
    filepath = os.path.join(settings.packs_path, filename)
    if os.path.exists(filepath):
        return filepath
    return None
