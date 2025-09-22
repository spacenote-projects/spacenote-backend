from datetime import datetime
from uuid import UUID

from pydantic import Field

from spacenote.core.db import MongoModel
from spacenote.utils import now


class Comment(MongoModel):
    """Comment on a note with threading support."""

    note_id: UUID
    space_id: UUID
    user_id: UUID
    number: int  # Sequential number per note
    content: str
    created_at: datetime = Field(default_factory=now)
    edited_at: datetime | None = None  # Future: editing
    parent_id: UUID | None = None  # Future: threading
