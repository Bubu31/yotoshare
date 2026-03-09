import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Archive, Pack
from app.schemas import DiscordPublishRequest, DiscordPublishPackRequest, DiscordPublishResponse
from app.auth import require_permission
from app.services.discord_bot import publish_archive, publish_pack
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/discord", tags=["discord"])


@router.post("/publish", response_model=DiscordPublishResponse)
async def publish_to_discord(
    data: DiscordPublishRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("discord", "modify")),
):
    try:
        archive = db.query(Archive).filter(Archive.id == data.archive_id).first()
        if not archive:
            return DiscordPublishResponse(
                success=False,
                message="Archive not found"
            )

        if archive.discord_post_id:
            return DiscordPublishResponse(
                success=False,
                message="Archive already published to Discord"
            )

        cover_url = None
        if archive.cover_path:
            cover_url = f"{settings.base_url}/api/archives/cover/{archive.cover_path}"

        # Parse chapters data
        chapters = None
        if archive.chapters_data:
            try:
                chapters = json.loads(archive.chapters_data)
            except json.JSONDecodeError:
                pass

        # Get category and age names for Discord tags
        tag_names = []
        if archive.categories:
            tag_names.extend([cat.name for cat in archive.categories])
        if archive.ages:
            tag_names.extend([age.name for age in archive.ages])

        post_id = await publish_archive(
            archive_id=archive.id,
            title=archive.title,
            author=archive.author,
            description=archive.description or "",
            cover_url=cover_url,
            file_size=archive.file_size,
            total_duration=archive.total_duration,
            chapters_count=archive.chapters_count,
            chapters=chapters,
            categories=tag_names if tag_names else None,
        )

        archive.discord_post_id = post_id
        db.commit()

        return DiscordPublishResponse(
            success=True,
            post_id=post_id,
            message="Archive published to Discord successfully"
        )
    except Exception as e:
        logger.error("Publish error: %s", e)
        return DiscordPublishResponse(
            success=False,
            message=f"Failed to publish: {str(e)}"
        )


@router.post("/publish-pack", response_model=DiscordPublishResponse)
async def publish_pack_to_discord(
    data: DiscordPublishPackRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("discord", "modify")),
):
    try:
        pack = db.query(Pack).filter(Pack.id == data.pack_id).first()
        if not pack:
            return DiscordPublishResponse(
                success=False,
                message="Pack not found"
            )

        if pack.discord_post_id:
            return DiscordPublishResponse(
                success=False,
                message="Pack already published to Discord"
            )

        image_url = None
        if pack.image_path:
            image_url = f"{settings.base_url}/api/packs/{pack.id}/image"

        total_size = sum(a.file_size for a in pack.archives)
        archive_titles = [a.title for a in pack.archives]

        post_id = await publish_pack(
            pack_id=pack.id,
            name=pack.name,
            description=pack.description or "",
            image_url=image_url,
            total_size=total_size,
            archive_titles=archive_titles,
        )

        pack.discord_post_id = post_id
        db.commit()

        return DiscordPublishResponse(
            success=True,
            post_id=post_id,
            message="Pack published to Discord successfully"
        )
    except Exception as e:
        logger.error("Publish pack error: %s", e)
        return DiscordPublishResponse(
            success=False,
            message=f"Failed to publish pack: {str(e)}"
        )
