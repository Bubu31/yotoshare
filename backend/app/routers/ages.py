from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.models import Age
from app.schemas import AgeResponse, AgeCreate, AgeUpdate
from app.auth import require_permission
from app.services.discord_client import create_forum_tag, delete_forum_tag

router = APIRouter(prefix="/api/ages", tags=["ages"])


@router.get("", response_model=List[AgeResponse])
async def list_ages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Age).order_by(Age.name))
    return result.scalars().all()


@router.post("", response_model=AgeResponse, status_code=status.HTTP_201_CREATED)
async def create_age(
    data: AgeCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ages", "modify")),
):
    result = await db.execute(select(Age).where(Age.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age already exists"
        )

    age = Age(**data.model_dump())
    db.add(age)
    await db.commit()
    await db.refresh(age)

    create_forum_tag(age.name, "👶")

    return age


@router.put("/{age_id}", response_model=AgeResponse)
async def update_age(
    age_id: int,
    data: AgeUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ages", "modify")),
):
    result = await db.execute(select(Age).where(Age.id == age_id))
    age = result.scalar_one_or_none()
    if not age:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Age not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(age, key, value)

    await db.commit()
    await db.refresh(age)
    return age


@router.delete("/{age_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_age(
    age_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ages", "delete")),
):
    result = await db.execute(select(Age).where(Age.id == age_id))
    age = result.scalar_one_or_none()
    if not age:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Age not found")

    age_name = age.name

    await db.delete(age)
    await db.commit()

    delete_forum_tag(age_name)
