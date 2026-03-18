from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Discord
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_forum_channel_id: str = ""

    # YotoShare API
    yotoshare_api_url: str = "http://yotoshare-backend:8000"

    # Shared inter-service key (same value as SERVICE_API_KEY in YotoShare)
    service_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
