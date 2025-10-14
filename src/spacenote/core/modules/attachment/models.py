from datetime import datetime
from uuid import UUID

from pydantic import Field

from spacenote.core.db import MongoModel
from spacenote.core.modules.attachment.utils import sanitize_filename
from spacenote.utils import now

SPACE_ATTACHMENTS_DIR = "__space__"


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

    def get_storage_path(self, note_number: int | None = None) -> str:
        """Calculate storage path from attachment properties.

        Args:
            note_number: Note number if attachment belongs to a note

        Returns:
            Relative path within attachments directory
        """
        sanitized = sanitize_filename(self.filename)
        file_part = f"{self.id}__{self.number}__{sanitized}"

        if note_number is not None:
            return f"{self.space_id}/{note_number}/{file_part}"
        return f"{self.space_id}/{SPACE_ATTACHMENTS_DIR}/{file_part}"
