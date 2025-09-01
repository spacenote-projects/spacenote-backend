from datetime import datetime
from uuid import UUID

from pydantic import Field

from spacenote.core.db import MongoModel
from spacenote.core.modules.field.models import FieldValueType
from spacenote.utils import now


class Note(MongoModel):
    """Note with custom fields stored in a space."""

    space_id: UUID
    number: int  # Sequential per space, used in URLs: /spaces/{slug}/notes/{number}
    author_id: UUID
    created_at: datetime = Field(default_factory=now)
    edited_at: datetime | None = None  # Last field edit timestamp
    fields: dict[str, FieldValueType]  # Values for space-defined fields
