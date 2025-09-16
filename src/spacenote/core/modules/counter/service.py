from typing import Any
from uuid import UUID

from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.counter.models import CounterType


class CounterService(Service):
    """Service for managing auto-incrementing counters per space."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("counters")

    async def on_start(self) -> None:
        """Create indexes on startup."""
        # Unique compound index for space_id and counter_type
        await self._collection.create_index([("space_id", 1), ("counter_type", 1)], unique=True)

    async def get_next_sequence(self, space_id: UUID, counter_type: CounterType) -> int:
        """Atomically increment and return the next sequence number for a space and type."""
        result = await self._collection.find_one_and_update(
            {"space_id": space_id, "counter_type": counter_type},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        # If it was just created (upserted), seq will be 1
        # Otherwise, it returns the incremented value
        return int(result["seq"])

    async def get_current_sequence(self, space_id: UUID, counter_type: CounterType) -> int:
        """Get the current sequence number without incrementing."""
        doc = await self._collection.find_one({"space_id": space_id, "counter_type": counter_type})
        if doc:
            return int(doc["seq"])
        return 0

    async def delete_counters_by_space(self, space_id: UUID) -> int:
        """Delete all counters for a space and return count of deleted counters."""
        result = await self._collection.delete_many({"space_id": space_id})
        return result.deleted_count
