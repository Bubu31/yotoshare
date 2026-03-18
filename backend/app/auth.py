import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[dict]:
    from app.models import User

    result = await db.execute(
        select(User).where(User.username == username).options(selectinload(User.role_rel))
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None

    permissions = {}
    role_name = "Éditeur"
    role_id = user.role_id

    if user.role_rel:
        role_name = user.role_rel.name
        try:
            permissions = json.loads(user.role_rel.permissions)
        except (json.JSONDecodeError, TypeError):
            permissions = {}
    else:
        if user.role == "admin":
            role_name = "Admin"

    return {
        "username": user.username,
        "role": user.role,
        "role_id": role_id,
        "role_name": role_name,
        "permissions": permissions,
    }


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    # Check X-Service-Key header first (inter-service auth)
    service_key = request.headers.get("X-Service-Key")
    if service_key and settings.service_api_key and service_key == settings.service_api_key:
        return {
            "username": "service",
            "role": "admin",
            "role_id": None,
            "role_name": "Admin",
            "permissions": {},
        }

    # Fall back to Bearer token auth
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role_name") != "Admin" and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_permission(scope: str, action: str):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        # Admin bypasses all permission checks
        if user.get("role_name") == "Admin" or user.get("role") == "admin":
            return user
        perms = user.get("permissions", {})
        if not perms.get(scope, {}).get(action, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission manquante: {scope}:{action}",
            )
        return user
    return checker
