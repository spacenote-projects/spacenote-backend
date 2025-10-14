from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.attachment.models import Attachment
from spacenote.core.modules.counter.models import CounterType
from spacenote.errors import NotFoundError

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

    async def get_attachment(self, attachment_id: UUID) -> Attachment:
        """Get attachment by ID.

        Args:
            attachment_id: The ID of the attachment

        Returns:
            The attachment

        Raises:
            NotFoundError: If attachment not found
        """
        doc = await self._collection.find_one({"_id": attachment_id})
        if not doc:
            raise NotFoundError(f"Attachment not found: {attachment_id}")
        return Attachment.model_validate(doc)

    async def create_attachment(
        self, space_id: UUID, note_id: UUID | None, user_id: UUID, filename: str, content: bytes, mime_type: str
    ) -> Attachment:
        """Create new attachment and save file to disk.

        Args:
            space_id: Space ID
            note_id: Note ID (None for space-level attachments)
            user_id: User who uploaded the file
            filename: Original filename
            content: File content bytes
            mime_type: MIME type

        Returns:
            Created attachment
        """
        number = await self.core.services.counter.get_next_sequence(space_id, CounterType.ATTACHMENT)
        attachment = Attachment(
            space_id=space_id,
            note_id=note_id,
            user_id=user_id,
            number=number,
            filename=filename,
            size=len(content),
            mime_type=mime_type,
        )

        storage_path = Path(self.core.config.attachments_path) / attachment.get_storage_path()
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)

        await self._collection.insert_one(attachment.model_dump(by_alias=True))
        logger.info("Created attachment", attachment_id=attachment.id, space_id=space_id, filename=filename)
        return attachment
