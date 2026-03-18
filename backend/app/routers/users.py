from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.models import User, Role
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.auth import require_permission, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def user_to_response(user: User) -> dict:
    """Convert User model to response dict with role_name."""
    role_name = None
    if user.role_rel:
        role_name = user.role_rel.name
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "role_id": user.role_id,
        "role_name": role_name,
        "created_at": user.created_at,
    }


async def _load_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role_rel))
    )
    return result.scalar_one_or_none()


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("users", "access")),
):
    result = await db.execute(
        select(User).order_by(User.created_at).options(selectinload(User.role_rel))
    )
    return [user_to_response(u) for u in result.scalars().all()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("users", "modify")),
):
    result = await db.execute(select(Role).where(Role.id == data.role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rôle introuvable",
        )

    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    role_str = "admin" if role.name == "Admin" else "editor"

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=role_str,
        role_id=data.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    user = await _load_user(db, user.id)
    return user_to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("users", "modify")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.role_id is not None:
        result = await db.execute(select(Role).where(Role.id == data.role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rôle introuvable",
            )
        user.role_id = data.role_id
        user.role = "admin" if role.name == "Admin" else "editor"

    if data.password is not None:
        user.password_hash = hash_password(data.password)

    await db.commit()

    user = await _load_user(db, user_id)
    return user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("users", "delete")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.username == current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    await db.delete(user)
    await db.commit()
