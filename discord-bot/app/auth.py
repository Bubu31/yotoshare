from fastapi import Request, HTTPException, status
from app.config import get_settings

settings = get_settings()


async def require_service_key(request: Request):
    """Dependency: validates X-Service-Key header for inter-service calls."""
    if not settings.service_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SERVICE_API_KEY not configured on discord-bot",
        )
    key = request.headers.get("X-Service-Key")
    if not key or key != settings.service_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Service-Key",
        )
