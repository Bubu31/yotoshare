"""Shared fixtures for all tests."""

import os
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

# Set test env vars BEFORE any app imports
os.environ.update({
    "SECRET_KEY": "test-secret-key",
    "DATABASE_URL": "sqlite:///./data/test.db",
    "NAS_MOUNT_PATH": "/tmp/nas-test",
    "BASE_URL": "http://localhost",
    "ADMIN_USERNAME": "testadmin",
    "ADMIN_PASSWORD_HASH": "notused",
    "DISCORD_BOT_TOKEN": "",
})

from app.config import get_settings, Settings
from app.database import Base, get_db
from app.auth import create_access_token
from app.main import app
from app.models import (
    Archive, Category, Age, User, Role, Pack, PackAsset,
    pack_archives, Submission,
)

# Sync engine for table creation and test data insertion
TEST_DB_URL = "sqlite:///./data/test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine for the FastAPI app dependency override
ASYNC_TEST_DB_URL = "sqlite+aiosqlite:///./data/test.db"
async_engine = create_async_engine(ASYNC_TEST_DB_URL)
AsyncTestSession = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a synchronous test database session (for fixture data insertion)."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def override_db(db):
    """Override the FastAPI get_db dependency with an async test session."""
    async def _get_test_db():
        async with AsyncTestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    """JWT token with admin privileges."""
    return create_access_token({
        "sub": "testadmin",
        "username": "testadmin",
        "role": "admin",
        "role_name": "Admin",
        "permissions": {},
    })


@pytest.fixture
def editor_token():
    """JWT token with editor privileges."""
    return create_access_token({
        "sub": "editor",
        "username": "editor",
        "role": "editor",
        "role_name": "Éditeur",
        "permissions": {
            "archives": {"access": True, "modify": True, "delete": False},
            "packs": {"access": True, "modify": True, "delete": False},
        },
    })


@pytest.fixture
def admin_headers(admin_token):
    """Auth headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def editor_headers(editor_token):
    """Auth headers for editor user."""
    return {"Authorization": f"Bearer {editor_token}"}


@pytest.fixture
async def client(override_db):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def sample_archives(db):
    """Create 25 sample archives for pagination tests."""
    archives = []
    for i in range(25):
        archive = Archive(
            title=f"Archive {i:03d}",
            author=f"Author {i % 5}",
            archive_path=f"archives/test-{i}.zip",
            file_size=1000 * (i + 1),
            download_count=i * 10,
            discord_post_id=f"discord_{i}" if i % 3 == 0 else None,
        )
        db.add(archive)
    db.commit()
    return db.query(Archive).order_by(Archive.created_at.desc()).all()


@pytest.fixture
def sample_categories(db):
    """Create sample categories."""
    cats = [
        Category(name="Musique", icon="fas fa-music"),
        Category(name="Histoire", icon="fas fa-book"),
    ]
    db.add_all(cats)
    db.commit()
    return cats


@pytest.fixture
def sample_packs(db, sample_archives):
    """Create 15 sample packs for pagination tests."""
    packs = []
    for i in range(15):
        pack = Pack(
            name=f"Pack {i:03d}",
            description=f"Description {i}",
            token=f"token_{i:03d}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(pack)
        db.flush()
        # Add 1-3 archives to each pack
        for j in range(min(i % 3 + 1, len(sample_archives))):
            db.execute(
                pack_archives.insert().values(
                    pack_id=pack.id,
                    archive_id=sample_archives[j].id,
                    position=j,
                )
            )
        packs.append(pack)
    db.commit()
    return packs
