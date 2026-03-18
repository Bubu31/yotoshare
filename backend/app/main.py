import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
from app.routers import (
    archives_router,
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
)
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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


@app.get("/api/health")
async def health_check():
    from fastapi.responses import JSONResponse
    from app.database import SessionLocal

    health_status = {"status": "healthy", "checks": {}}
    is_healthy = True

    # Check database connectivity
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        is_healthy = False

    if not is_healthy:
        health_status["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=health_status)

    return health_status
