import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401

    # Run Alembic migrations (creates tables + applies all migrations)
    from alembic.config import Config
    from alembic import command
    import os

    alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied")

    # Seed admin user from env vars if no users exist
    seed_admin_user()


def seed_admin_user():
    """Create the initial admin user from env vars if the users table is empty."""
    from app.models import User, Role

    db = SessionLocal()
    try:
        # Ensure admin user has role_id set
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
