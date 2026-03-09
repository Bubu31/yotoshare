import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models import DownloadToken, Archive

settings = get_settings()


def generate_signed_token(archive_id: int, expiry_timestamp: int) -> str:
    random_part = secrets.token_hex(16)
    data = f"{archive_id}:{expiry_timestamp}:{random_part}"
    signature = hmac.new(
        settings.secret_key.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return f"{random_part}{signature}"


def create_download_token(
    db: Session,
    archive_id: int,
    discord_user_id: Optional[str] = None,
    expiry_seconds: Optional[int] = None,
    reusable: bool = False,
) -> tuple[str, datetime]:
    expiry = expiry_seconds if expiry_seconds is not None else settings.download_link_expiry
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiry)
    expiry_timestamp = int(expires_at.timestamp())

    token = generate_signed_token(archive_id, expiry_timestamp)

    db_token = DownloadToken(
        token=token,
        archive_id=archive_id,
        discord_user_id=discord_user_id,
        expires_at=expires_at,
        reusable=reusable,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    return token, expires_at


def validate_token(db: Session, token: str) -> Optional[Archive]:
    db_token = db.query(DownloadToken).filter(DownloadToken.token == token).first()
    if not db_token:
        return None

    # Handle both timezone-aware and naive datetimes from database
    expires_at = db_token.expires_at
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        # Database returned naive datetime, assume it's UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        return None

    if db_token.used and not db_token.reusable:
        return None

    return db_token.archive


def mark_token_used(db: Session, token: str) -> bool:
    db_token = db.query(DownloadToken).filter(DownloadToken.token == token).first()
    if db_token:
        db_token.used = True
        db.commit()
        return True
    return False


def cleanup_expired_tokens(db: Session) -> int:
    now = datetime.now(timezone.utc)
    result = db.query(DownloadToken).filter(DownloadToken.expires_at < now).delete()
    db.commit()
    return result


def get_download_url(token: str) -> str:
    return f"{settings.base_url}/share/{token}"


def create_pack_signed_url(pack_id: int, expiry_seconds: Optional[int] = None) -> tuple[str, datetime]:
    """Generate a signed download URL for a pack (no DB, HMAC-based)."""
    expiry = expiry_seconds if expiry_seconds is not None else settings.download_link_expiry
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiry)
    expiry_ts = int(expires_at.timestamp())
    data = f"pack:{pack_id}:{expiry_ts}"
    signature = hmac.new(
        settings.secret_key.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()[:32]
    token = f"{pack_id}.{expiry_ts}.{signature}"
    url = f"{settings.base_url}/api/packs/signed-download/{token}"
    return url, expires_at


def validate_pack_signed_token(token: str) -> Optional[int]:
    """Validate a pack signed token, return pack_id or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        pack_id = int(parts[0])
        expiry_ts = int(parts[1])
        signature = parts[2]

        # Check expiry
        now = datetime.now(timezone.utc)
        if now.timestamp() > expiry_ts:
            return None

        # Verify signature
        data = f"pack:{pack_id}:{expiry_ts}"
        expected = hmac.new(
            settings.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        if not hmac.compare_digest(signature, expected):
            return None

        return pack_id
    except (ValueError, IndexError):
        return None
