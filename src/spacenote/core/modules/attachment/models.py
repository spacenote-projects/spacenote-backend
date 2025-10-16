from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel
from spacenote.utils import now


class Attachment(MongoModel):
    """File attachment that belongs to a space and optionally to a note."""

    space_id: UUID
    note_id: UUID | None = None
    user_id: UUID
    number: int  # Sequential per space (globally unique within space)

    filename: str  # Original filename from user
    size: int  # File size in bytes
    mime_type: str  # Content type (e.g., "image/png")

    created_at: datetime = Field(default_factory=now)


class AttachmentFileInfo(BaseModel):
    """Information about an attachment file for download."""

    file_path: Path = Field(..., description="Absolute path to file on disk")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type")
