from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List, Dict


# Category schemas
class CategoryBase(BaseModel):
    name: str
    icon: str = "fa-folder"


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# Age schemas
class AgeBase(BaseModel):
    name: str
    icon: str = "fa-child"


class AgeCreate(AgeBase):
    pass


class AgeUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class AgeResponse(AgeBase):
    id: int

    class Config:
        from_attributes = True


# Archive schemas
class ArchiveBase(BaseModel):
    title: str
    author: Optional[str] = None
    description: Optional[str] = None


class ArchiveCreate(ArchiveBase):
    category_ids: Optional[List[int]] = None
    age_ids: Optional[List[int]] = None


class ArchiveUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    category_ids: Optional[List[int]] = None
    age_ids: Optional[List[int]] = None


class ChapterInfo(BaseModel):
    key: Optional[str] = None
    title: Optional[str] = None
    label: Optional[str] = None
    duration: Optional[int] = None
    icon: Optional[str] = None


class ArchiveResponse(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    cover_path: Optional[str] = None
    archive_path: str
    file_size: int
    total_duration: Optional[int] = None
    chapters_count: Optional[int] = None
    chapters: Optional[List[ChapterInfo]] = None
    discord_post_id: Optional[str] = None
    download_count: int = 0
    created_at: datetime
    updated_at: datetime
    categories: List[CategoryResponse] = []
    ages: List[AgeResponse] = []

    @field_validator("total_duration", mode="before")
    @classmethod
    def coerce_duration_to_int(cls, v):
        return int(v) if v is not None else None

    class Config:
        from_attributes = True


class ArchiveListResponse(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    cover_path: Optional[str] = None
    file_size: int
    total_duration: Optional[int] = None
    chapters_count: Optional[int] = None
    discord_post_id: Optional[str] = None
    download_count: int = 0
    categories: List[CategoryResponse] = []
    ages: List[AgeResponse] = []
    created_at: datetime

    @field_validator("total_duration", mode="before")
    @classmethod
    def coerce_duration_to_int(cls, v):
        return int(v) if v is not None else None

    class Config:
        from_attributes = True


# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class PermissionSet(BaseModel):
    access: bool = False
    modify: bool = False
    delete: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    role_id: Optional[int] = None
    role_name: str = ""
    permissions: Dict[str, PermissionSet] = {}


# Download token schemas
class DownloadTokenCreate(BaseModel):
    archive_id: int
    discord_user_id: Optional[str] = None
    expiry_seconds: Optional[int] = None
    reusable: bool = False


class DownloadTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    download_url: str


# Discord schemas
class DiscordPublishRequest(BaseModel):
    archive_id: int


class DiscordPublishPackRequest(BaseModel):
    pack_id: int


class DiscordPublishResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    message: str


# User schemas
class UserCreate(BaseModel):
    username: str
    password: str
    role_id: int


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role_id: Optional[int] = None


# Role schemas
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Dict[str, PermissionSet]


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[Dict[str, PermissionSet]] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: Dict[str, PermissionSet] = {}
    is_system: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Archive Editor schemas
class ChapterDetail(BaseModel):
    key: str
    title: Optional[str] = None
    label: Optional[str] = None
    duration: Optional[int] = None
    audio_file: Optional[str] = None
    icon_file: Optional[str] = None
    order: int


class ArchiveContent(BaseModel):
    id: int
    title: str
    chapters: List[ChapterDetail]
    has_cover: bool = False
    nfo: Optional[str] = None


class ChapterUpdate(BaseModel):
    key: str
    title: Optional[str] = None
    label: Optional[str] = None
    order: Optional[int] = None
    delete: bool = False


class ChaptersUpdateRequest(BaseModel):
    chapters: List[ChapterUpdate]


class CropData(BaseModel):
    x: int
    y: int
    width: int
    height: int


class SplitRequest(BaseModel):
    split_points: List[int]


class TrimRequest(BaseModel):
    start_ms: int
    end_ms: int
    mode: str = "keep"


class MergeRequest(BaseModel):
    chapter_keys: List[str]
    new_title: str


class NfoUpdateRequest(BaseModel):
    content: str


class WaveformResponse(BaseModel):
    duration_ms: int
    samples: List[float]


# Pack schemas
# Submission schemas
class SubmissionResponse(BaseModel):
    id: int
    pseudonym: Optional[str] = None
    title: Optional[str] = None
    cover_path: Optional[str] = None
    archive_path: str
    file_size: int = 0
    total_duration: Optional[int] = None
    chapters_count: Optional[int] = None
    chapters_data: Optional[str] = None
    status: str = "pending"
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rework_comment: Optional[str] = None
    parent_submission_id: Optional[int] = None
    created_at: datetime

    @field_validator("total_duration", mode="before")
    @classmethod
    def coerce_duration_to_int(cls, v):
        return int(v) if v is not None else None

    class Config:
        from_attributes = True


class ReworkSubmissionResponse(BaseModel):
    id: int
    pseudonym: Optional[str] = None
    title: Optional[str] = None
    cover_path: Optional[str] = None
    file_size: int = 0
    total_duration: Optional[int] = None
    chapters_count: Optional[int] = None
    chapters_data: Optional[str] = None
    rework_comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    @field_validator("total_duration", mode="before")
    @classmethod
    def coerce_duration_to_int(cls, v):
        return int(v) if v is not None else None

    class Config:
        from_attributes = True


class SubmissionReviewRequest(BaseModel):
    action: str  # "approve", "reject", or "rework"
    rejection_reason: Optional[str] = None
    rework_comment: Optional[str] = None


# Pack schemas
class PackCreate(BaseModel):
    name: str
    description: Optional[str] = None
    archive_ids: List[int]


class PackUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    archive_ids: Optional[List[int]] = None


class PackArchiveInfo(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    cover_path: Optional[str] = None
    file_size: int

    class Config:
        from_attributes = True


class PackResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    token: str
    image_path: Optional[str] = None
    discord_post_id: Optional[str] = None
    expires_at: datetime
    archive_count: int
    archives: List[PackArchiveInfo] = []
    share_url: str
    created_at: datetime

    class Config:
        from_attributes = True
