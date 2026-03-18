from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Age
from app.schemas import AgeResponse, AgeCreate, AgeUpdate
from app.auth import require_permission
from app.services.discord_client import create_forum_tag, delete_forum_tag

router = APIRouter(prefix="/api/ages", tags=["ages"])


@router.get("", response_model=List[AgeResponse])
async def list_ages(db: Session = Depends(get_db)):
    return db.query(Age).order_by(Age.name).all()


@router.post("", response_model=AgeResponse, status_code=status.HTTP_201_CREATED)
async def create_age(
    data: AgeCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("ages", "modify")),
):
    existing = db.query(Age).filter(Age.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age already exists"
        )

    age = Age(**data.model_dump())
    db.add(age)
    db.commit()
    db.refresh(age)

    # Create corresponding Discord forum tag with baby emoji
    create_forum_tag(age.name, "👶")

    return age


@router.put("/{age_id}", response_model=AgeResponse)
async def update_age(
    age_id: int,
    data: AgeUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("ages", "modify")),
):
    age = db.query(Age).filter(Age.id == age_id).first()
    if not age:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Age not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(age, key, value)

    db.commit()
    db.refresh(age)
    return age


@router.delete("/{age_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_age(
    age_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("ages", "delete")),
):
    age = db.query(Age).filter(Age.id == age_id).first()
    if not age:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Age not found")

    age_name = age.name

    db.delete(age)
    db.commit()

    # Delete corresponding Discord forum tag
    delete_forum_tag(age_name)
