from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
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


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users", "access")),
):
    users = db.query(User).order_by(User.created_at).all()
    return [user_to_response(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users", "modify")),
):
    # Validate role_id exists
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rôle introuvable",
        )

    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Map role_id to old role string for backwards compat
    role_str = "editor"
    if role.name == "Admin":
        role_str = "admin"

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=role_str,
        role_id=data.role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("users", "modify")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.role_id is not None:
        role = db.query(Role).filter(Role.id == data.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rôle introuvable",
            )
        user.role_id = data.role_id
        # Update old role string for backwards compat
        user.role = "admin" if role.name == "Admin" else "editor"

    if data.password is not None:
        user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("users", "delete")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.username == current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    db.delete(user)
    db.commit()
