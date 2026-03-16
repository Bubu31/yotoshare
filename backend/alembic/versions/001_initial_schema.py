"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-16

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Roles
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.Text(), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("icon", sa.String(50), server_default="fas fa-folder"),
    )
    op.create_index("ix_categories_id", "categories", ["id"])

    # Ages
    op.create_table(
        "ages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("icon", sa.String(50), server_default="fas fa-child"),
    )
    op.create_index("ix_ages_id", "ages", ["id"])

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="editor"),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Archives
    op.create_table(
        "archives",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_path", sa.String(500), nullable=True),
        sa.Column("archive_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_duration", sa.Integer(), nullable=True),
        sa.Column("chapters_count", sa.Integer(), nullable=True),
        sa.Column("chapters_data", sa.Text(), nullable=True),
        sa.Column("discord_post_id", sa.String(50), nullable=True),
        sa.Column("download_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_archives_id", "archives", ["id"])
    op.create_index("ix_archives_title", "archives", ["title"])
    op.create_index("ix_archives_discord_post_id", "archives", ["discord_post_id"])

    # Archive ↔ Category association
    op.create_table(
        "archive_categories",
        sa.Column("archive_id", sa.Integer(), sa.ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    )

    # Archive ↔ Age association
    op.create_table(
        "archive_ages",
        sa.Column("archive_id", sa.Integer(), sa.ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("age_id", sa.Integer(), sa.ForeignKey("ages.id", ondelete="CASCADE"), primary_key=True),
    )

    # Download tokens
    op.create_table(
        "download_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("archive_id", sa.Integer(), sa.ForeignKey("archives.id"), nullable=False),
        sa.Column("discord_user_id", sa.String(50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("reusable", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_download_tokens_id", "download_tokens", ["id"])
    op.create_index("ix_download_tokens_token", "download_tokens", ["token"], unique=True)
    op.create_index("ix_download_tokens_expires_at", "download_tokens", ["expires_at"])

    # Packs
    op.create_table(
        "packs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("discord_post_id", sa.String(50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_packs_id", "packs", ["id"])
    op.create_index("ix_packs_token", "packs", ["token"], unique=True)
    op.create_index("ix_packs_expires_at", "packs", ["expires_at"])
    op.create_index("ix_packs_discord_post_id", "packs", ["discord_post_id"])

    # Pack ↔ Archive association
    op.create_table(
        "pack_archives",
        sa.Column("pack_id", sa.Integer(), sa.ForeignKey("packs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("archive_id", sa.Integer(), sa.ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer(), server_default=sa.text("0")),
    )

    # Pack assets
    op.create_table(
        "pack_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_type", sa.String(50), unique=True, nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pack_assets_id", "pack_assets", ["id"])

    # Submissions
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pseudonym", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("cover_path", sa.String(500), nullable=True),
        sa.Column("archive_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_duration", sa.Integer(), nullable=True),
        sa.Column("chapters_count", sa.Integer(), nullable=True),
        sa.Column("chapters_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("submitter_ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_submissions_id", "submissions", ["id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])

    # Seed default roles
    all_scopes = ["archives", "categories", "ages", "users", "roles", "discord", "packs", "submissions"]
    admin_perms = {scope: {"access": True, "modify": True, "delete": True} for scope in all_scopes}
    editor_perms = {}
    for scope in all_scopes:
        if scope in ("users", "roles"):
            editor_perms[scope] = {"access": False, "modify": False, "delete": False}
        else:
            editor_perms[scope] = {"access": True, "modify": True, "delete": False}

    roles_table = sa.table(
        "roles",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("permissions", sa.Text),
        sa.column("is_system", sa.Boolean),
    )
    op.bulk_insert(roles_table, [
        {"name": "Admin", "description": "Accès complet à toutes les fonctionnalités", "permissions": json.dumps(admin_perms), "is_system": True},
        {"name": "Éditeur", "description": "Accès en lecture et modification, pas de suppression", "permissions": json.dumps(editor_perms), "is_system": True},
    ])


def downgrade() -> None:
    op.drop_table("submissions")
    op.drop_table("pack_assets")
    op.drop_table("pack_archives")
    op.drop_table("packs")
    op.drop_table("download_tokens")
    op.drop_table("archive_ages")
    op.drop_table("archive_categories")
    op.drop_table("archives")
    op.drop_table("users")
    op.drop_table("ages")
    op.drop_table("categories")
    op.drop_table("roles")
