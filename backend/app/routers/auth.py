from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import LoginRequest, TokenResponse
from app.auth import authenticate_user, create_access_token
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    access_token = create_access_token(data={
        "sub": user["username"],
        "role": user["role"],
        "role_id": user.get("role_id"),
        "role_name": user.get("role_name", ""),
        "permissions": user.get("permissions", {}),
    })
    return TokenResponse(
        access_token=access_token,
        role=user["role"],
        role_id=user.get("role_id"),
        role_name=user.get("role_name", ""),
        permissions=user.get("permissions", {}),
    )
