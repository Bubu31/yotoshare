import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
from app.routers import (
    archives_router,
    archive_uploads_router,
    categories_router,
    ages_router,
    download_router,
    discord_router,
    auth_router,
    users_router,
    share_router,
    roles_router,
    packs_router,
    submissions_router,
    service_router,
    uploads_router,
)
from app.config import get_settings
from app.services import storage
from app.models import UploadSession
from app.database import AsyncSessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)

GC_INTERVAL_SECONDS = 600       # run GC every 10 minutes
ARCHIVE_CACHE_TTL_SECONDS = 1800  # 30 minutes idle → evict
UPLOAD_CLEANUP_INTERVAL_SECONDS = 1800  # every 30 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def _gc_loop():
        while True:
            await asyncio.sleep(GC_INTERVAL_SECONDS)
            try:
                n = storage.cleanup_old_archive_data(ARCHIVE_CACHE_TTL_SECONDS)
                if n:
                    logger.info("Archive cache GC: removed %d expired extraction(s)", n)
            except Exception as exc:
                logger.warning("Archive cache GC error: %s", exc)

    async def _upload_cleanup_loop():
        while True:
            await asyncio.sleep(UPLOAD_CLEANUP_INTERVAL_SECONDS)
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(UploadSession).where(
                            UploadSession.expires_at < datetime.now(timezone.utc)
                        )
                    )
                    expired_sessions = result.scalars().all()
                    for session in expired_sessions:
                        await asyncio.to_thread(storage.cleanup_chunks, session.upload_id)
                        await db.delete(session)
                    if expired_sessions:
                        await db.commit()
                        logger.info("Upload cleanup: removed %d expired session(s)", len(expired_sessions))
            except Exception as exc:
                logger.warning("Upload cleanup error: %s", exc)

    gc_task = asyncio.create_task(_gc_loop())
    upload_cleanup_task = asyncio.create_task(_upload_cleanup_loop())
    yield
    gc_task.cancel()
    upload_cleanup_task.cancel()
    try:
        await gc_task
    except asyncio.CancelledError:
        pass
    try:
        await upload_cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="YotoShare API",
    description="API for managing MYO Studio archives and sharing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(archives_router)
app.include_router(archive_uploads_router)
app.include_router(categories_router)
app.include_router(ages_router)
app.include_router(download_router)
app.include_router(discord_router)
app.include_router(users_router)
app.include_router(share_router)
app.include_router(roles_router)
app.include_router(packs_router)
app.include_router(submissions_router)
app.include_router(service_router)
app.include_router(uploads_router)


@app.get("/api/health")
async def health_check():
    from fastapi.responses import JSONResponse
    from sqlalchemy import text
    from app.database import AsyncSessionLocal

    health_status = {"status": "healthy", "checks": {}}
    is_healthy = True

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        is_healthy = False

    if not is_healthy:
        health_status["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=health_status)

    return health_status
