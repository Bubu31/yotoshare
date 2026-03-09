"""Re-import archives from existing ZIP files on the NAS.

Scans the archives directory for ZIP files that are not in the database,
extracts metadata and covers, and creates Archive records.

Usage:
    docker exec yoto-library-backend python scripts/reimport_archives.py
    docker exec yoto-library-backend python scripts/reimport_archives.py --dry-run
"""

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.database import SessionLocal
from app.models import Archive
from app.services import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()


def run_reimport(dry_run=False):
    archives_dir = settings.archives_path
    if not os.path.isdir(archives_dir):
        logger.error("Archives directory not found: %s", archives_dir)
        sys.exit(1)

    # Scan ZIP files
    zip_files = sorted(
        f for f in os.listdir(archives_dir)
        if f.endswith(".zip") and not f.startswith(".")
    )

    if not zip_files:
        logger.info("No ZIP files found in %s", archives_dir)
        return

    logger.info("Found %d ZIP files in %s", len(zip_files), archives_dir)

    db = SessionLocal()
    stats = {"imported": 0, "skipped": 0, "errors": 0}

    try:
        # Get existing archive filenames to skip
        existing = set(
            row[0] for row in db.query(Archive.archive_path).all()
        )
        logger.info("Already in DB: %d archives", len(existing))

        for i, filename in enumerate(zip_files, 1):
            if filename in existing:
                logger.debug("Skipping existing: %s", filename)
                stats["skipped"] += 1
                continue

            filepath = os.path.join(archives_dir, filename)
            file_size = os.path.getsize(filepath)

            try:
                metadata = storage.extract_archive_metadata(filepath)
                title = metadata.get("title") or filename.replace(".zip", "")

                if dry_run:
                    logger.info(
                        "  [%d/%d] %s → title=%r, chapters=%s, duration=%s",
                        i, len(zip_files), filename, title,
                        metadata.get("chapters_count") or 0,
                        metadata.get("total_duration") or "?",
                    )
                    stats["imported"] += 1
                    continue

                # Save cover if present
                cover_filename = None
                if metadata.get("cover_data"):
                    cover_filename = asyncio.run(
                        storage.save_cover_from_bytes(metadata["cover_data"])
                    )

                # Build chapters JSON
                chapters_json = None
                if metadata.get("chapters"):
                    chapters_json = json.dumps(metadata["chapters"])

                archive = Archive(
                    title=title,
                    archive_path=filename,
                    cover_path=cover_filename,
                    file_size=file_size,
                    total_duration=metadata.get("total_duration"),
                    chapters_count=metadata.get("chapters_count"),
                    chapters_data=chapters_json,
                )
                db.add(archive)
                stats["imported"] += 1

                if stats["imported"] % 10 == 0:
                    db.commit()
                    logger.info("Progress: %d/%d", i, len(zip_files))

            except Exception:
                logger.exception("Error importing %s", filename)
                stats["errors"] += 1
                continue

        if not dry_run:
            db.commit()

    except Exception:
        logger.exception("Fatal error")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

    logger.info("=" * 50)
    logger.info("Re-import complete!")
    logger.info("  ZIP files found  : %d", len(zip_files))
    logger.info("  Imported         : %d", stats["imported"])
    logger.info("  Skipped (in DB)  : %d", stats["skipped"])
    logger.info("  Errors           : %d", stats["errors"])


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("=== DRY RUN ===")
    run_reimport(dry_run=dry_run)
