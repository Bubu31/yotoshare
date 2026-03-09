import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Role, User
from app.schemas import RoleCreate, RoleUpdate, RoleResponse
from app.auth import require_permission

router = APIRouter(prefix="/api/roles", tags=["roles"])


def role_to_response(role: Role) -> dict:
    """Convert Role model to response dict with parsed permissions."""
    permissions = {}
    try:
        permissions = json.loads(role.permissions)
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": permissions,
        "is_system": role.is_system,
        "created_at": role.created_at,
    }


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("roles", "access")),
):
    roles = db.query(Role).order_by(Role.id).all()
    return [role_to_response(r) for r in roles]


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("roles", "access")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rôle introuvable")
    return role_to_response(role)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("roles", "modify")),
):
    existing = db.query(Role).filter(Role.name == data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un rôle avec ce nom existe déjà")

    permissions_json = json.dumps({k: v.model_dump() for k, v in data.permissions.items()})

    role = Role(
        name=data.name,
        description=data.description,
        permissions=permissions_json,
        is_system=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role_to_response(role)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("roles", "modify")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rôle introuvable")

    # Cannot modify Admin role permissions
    if role.name == "Admin" and data.permissions is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de modifier les permissions du rôle Admin",
        )

    if data.name is not None:
        # Cannot rename system roles
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de renommer un rôle système",
            )
        existing = db.query(Role).filter(Role.name == data.name, Role.id != role_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un rôle avec ce nom existe déjà")
        role.name = data.name

    if data.description is not None:
        role.description = data.description

    if data.permissions is not None:
        role.permissions = json.dumps({k: v.model_dump() for k, v in data.permissions.items()})

    db.commit()
    db.refresh(role)
    return role_to_response(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("roles", "delete")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rôle introuvable")

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un rôle système",
        )

    # Check if any users are assigned to this role
    user_count = db.query(User).filter(User.role_id == role_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de supprimer ce rôle : {user_count} utilisateur(s) assigné(s)",
        )

    db.delete(role)
    db.commit()
