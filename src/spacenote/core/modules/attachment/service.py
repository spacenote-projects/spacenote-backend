from typing import Any

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service

logger = structlog.get_logger(__name__)


class AttachmentService(Service):
    """Manages file attachments for spaces and notes."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("attachments")

    async def on_start(self) -> None:
        """Create indexes for attachment lookup."""
        await self._collection.create_index([("space_id", 1), ("number", 1)], unique=True)
        await self._collection.create_index([("note_id", 1)])
        await self._collection.create_index([("user_id", 1)])
        await self._collection.create_index([("created_at", -1)])
