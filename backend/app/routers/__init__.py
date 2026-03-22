from app.routers.archives import router as archives_router
from app.routers.archive_uploads import router as archive_uploads_router
from app.routers.categories import router as categories_router
from app.routers.ages import router as ages_router
from app.routers.download import router as download_router
from app.routers.discord import router as discord_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.share import router as share_router
from app.routers.roles import router as roles_router
from app.routers.packs import router as packs_router
from app.routers.submissions import router as submissions_router
from app.routers.service import router as service_router
from app.routers.uploads import router as uploads_router

__all__ = [
    "archives_router",
    "archive_uploads_router",
    "categories_router",
    "ages_router",
    "download_router",
    "discord_router",
    "auth_router",
    "users_router",
    "share_router",
    "roles_router",
    "packs_router",
    "submissions_router",
    "service_router",
    "uploads_router",
]
