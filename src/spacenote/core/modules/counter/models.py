"""Auto-incrementing counters for sequential numbering."""

from enum import StrEnum
from uuid import UUID

from spacenote.core.db import MongoModel


class CounterType(StrEnum):
    """Types of entities that use sequential numbering."""

    NOTE = "note"
    ATTACHMENT = "attachment"


class Counter(MongoModel):
    """Atomic counter for sequential numbers per space.

    Uses MongoDB atomic operations to prevent duplicates.
    Indexed on (space_id, counter_type) - unique.
    """

    space_id: UUID
    counter_type: CounterType
    seq: int = 0  # Current value; next number will be seq + 1
