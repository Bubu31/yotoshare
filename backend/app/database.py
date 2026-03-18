import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _make_async_url(url: str) -> str:
    """Convert a sync database URL to its async driver equivalent."""
    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Async engine + session (used by the app)
engine = create_async_engine(_make_async_url(settings.database_url))
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Sync engine + session (used by CLI scripts: init_db, seed_admin_user, Alembic)
_sync_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _sync_connect_args["check_same_thread"] = False
_sync_engine = create_engine(settings.database_url, connect_args=_sync_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_sync_engine)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def init_db():
    from app import models  # noqa: F401

    from alembic.config import Config
    from alembic import command
    import os

    alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied")

    seed_admin_user()


def seed_admin_user():
    """Create the initial admin user from env vars if the users table is empty."""
    from app.models import User, Role

    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "Admin").first()

        if db.query(User).count() == 0:
            username = settings.admin_username
            password_hash = settings.admin_password_hash
            if username and password_hash:
                admin = User(
                    username=username,
                    password_hash=password_hash,
                    role="admin",
                    role_id=admin_role.id if admin_role else None,
                )
                db.add(admin)
                db.commit()
                logger.info("Created admin user: %s", username)
            else:
                logger.warning("No admin credentials in env vars, skipping seed")
        else:
            logger.debug("Users table not empty, skipping seed")
    finally:
        db.close()
