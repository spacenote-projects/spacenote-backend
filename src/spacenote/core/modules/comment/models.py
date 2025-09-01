from datetime import datetime
from uuid import UUID

from pydantic import Field

from spacenote.core.db import MongoModel
from spacenote.utils import now


class Comment(MongoModel):
    note_id: UUID
    space_id: UUID
    author_id: UUID
    number: int  # Sequential number for comments within a note
    content: str
    created_at: datetime = Field(default_factory=now)
    edited_at: datetime | None = None  # for future editing functionality
    parent_id: UUID | None = None  # for future threading functionality
