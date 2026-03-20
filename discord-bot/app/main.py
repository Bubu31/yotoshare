import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.bot import bot, bot_ready, bot_error, start_bot
from app.config import get_settings
from app.routers.publish import router as publish_router
from app.routers.thread import router as thread_router
from app.routers.tag import router as tag_router
from app.routers.notify import router as notify_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_task = None
    if settings.discord_bot_token:
        bot_task = asyncio.create_task(start_bot())
        logger.info("Discord bot started in main event loop")
    else:
        logger.warning("DISCORD_BOT_TOKEN not set — bot will not start")
    yield
    if bot_task and not bot_task.done():
        await bot.close()
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="YotoShare Discord Bot", version="1.0.0", lifespan=lifespan)

app.include_router(publish_router)
app.include_router(thread_router)
app.include_router(tag_router)
app.include_router(notify_router)


@app.get("/health")
async def health():
    status_info = {"status": "healthy", "checks": {}}
    is_healthy = True

    if settings.discord_bot_token:
        if bot_error:
            status_info["checks"]["discord_bot"] = f"error: {bot_error}"
            is_healthy = False
        elif not bot_ready.is_set():
            status_info["checks"]["discord_bot"] = "starting"
        elif bot.is_closed():
            status_info["checks"]["discord_bot"] = "disconnected"
            is_healthy = False
        else:
            status_info["checks"]["discord_bot"] = "connected"
    else:
        status_info["checks"]["discord_bot"] = "disabled"

    if not is_healthy:
        status_info["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=status_info)

    return status_info
