import logging
from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Backend
    secret_key: str = "change-me-in-production"
    admin_username: str = "admin"
    admin_password_hash: str = ""

    # Database
    database_url: str = "sqlite:///./data/yotoshare.db"

    # Storage
    nas_mount_path: str = "/mnt/nas/myo"
    archives_dir: str = "archives"
    covers_dir: str = "covers"
    packs_dir: str = "packs"

    # Discord bot service URL (external service)
    discord_bot_url: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173"

    # App
    base_url: str = "http://localhost"
    download_link_expiry: int = 7200

    # Service API Key (for inter-service auth)
    service_api_key: str = ""

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    @model_validator(mode='after')
    def validate_settings(self):
        if self.secret_key == "change-me-in-production" and "localhost" not in self.base_url:
            logger.warning("SECRET_KEY is using default value in non-localhost environment!")
        if not self.admin_password_hash:
            logger.warning("ADMIN_PASSWORD_HASH is empty — admin user will not be seeded")
        return self

    @property
    def archives_path(self) -> str:
        return f"{self.nas_mount_path}/{self.archives_dir}"

    @property
    def covers_path(self) -> str:
        return f"{self.nas_mount_path}/{self.covers_dir}"

    @property
    def packs_path(self) -> str:
        return f"{self.nas_mount_path}/{self.packs_dir}"

    @property
    def pack_assets_path(self) -> str:
        return f"{self.nas_mount_path}/{self.packs_dir}/assets"

    @property
    def submissions_data_path(self) -> str:
        return f"{self.nas_mount_path}/submissions-data"

    @property
    def archives_data_path(self) -> str:
        return f"{self.nas_mount_path}/archives-data"

    class Config:
        env_file = (".env", "../.env")
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
