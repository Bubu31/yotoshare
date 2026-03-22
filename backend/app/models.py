from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=False)  # JSON string
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Association tables for many-to-many relationships
archive_categories = Table(
    "archive_categories",
    Base.metadata,
    Column("archive_id", Integer, ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)

archive_ages = Table(
    "archive_ages",
    Base.metadata,
    Column("archive_id", Integer, ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True),
    Column("age_id", Integer, ForeignKey("ages.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50), default="fas fa-folder")

    archives = relationship("Archive", secondary=archive_categories, back_populates="categories")


class Age(Base):
    __tablename__ = "ages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    icon = Column(String(50), default="fas fa-child")

    archives = relationship("Archive", secondary=archive_ages, back_populates="ages")


class Archive(Base):
    __tablename__ = "archives"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cover_path = Column(String(500), nullable=True)
    archive_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    total_duration = Column(Integer, nullable=True)
    chapters_count = Column(Integer, nullable=True)
    chapters_data = Column(Text, nullable=True)
    discord_post_id = Column(String(50), nullable=True, index=True)
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    categories = relationship("Category", secondary=archive_categories, back_populates="archives")
    ages = relationship("Age", secondary=archive_ages, back_populates="archives")
    download_tokens = relationship("DownloadToken", back_populates="archive", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="editor")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role_rel = relationship("Role")


pack_archives = Table(
    "pack_archives",
    Base.metadata,
    Column("pack_id", Integer, ForeignKey("packs.id", ondelete="CASCADE"), primary_key=True),
    Column("archive_id", Integer, ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True),
    Column("position", Integer, default=0),
)


class Pack(Base):
    __tablename__ = "packs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    image_path = Column(String(500), nullable=True)
    discord_post_id = Column(String(50), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    archives = relationship("Archive", secondary=pack_archives, order_by=pack_archives.c.position)
    creator = relationship("User")


class PackAsset(Base):
    __tablename__ = "pack_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String(50), unique=True, nullable=False)
    filename = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    pseudonym = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    cover_path = Column(String(500), nullable=True)
    archive_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    total_duration = Column(Integer, nullable=True)
    chapters_count = Column(Integer, nullable=True)
    chapters_data = Column(Text, nullable=True)
    status = Column(String(20), default="pending", index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rework_comment = Column(Text, nullable=True)
    parent_submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)
    submitter_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reviewer = relationship("User")
    parent_submission = relationship("Submission", remote_side="Submission.id", foreign_keys=[parent_submission_id])


class DownloadToken(Base):
    __tablename__ = "download_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    archive_id = Column(Integer, ForeignKey("archives.id"), nullable=False)
    discord_user_id = Column(String(50), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used = Column(Boolean, default=False)
    reusable = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    archive = relationship("Archive", back_populates="download_tokens")


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    upload_id = Column(String(36), primary_key=True, index=True)  # UUID4
    filename = Column(String(500), nullable=False)
    total_size = Column(Integer, nullable=False)
    total_chunks = Column(Integer, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    pseudonym = Column(String(255), nullable=True)
    parent_submission_id = Column(Integer, nullable=True)
    submitter_ip = Column(String(45), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
