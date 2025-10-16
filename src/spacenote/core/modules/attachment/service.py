from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.attachment.models import Attachment, AttachmentFileInfo
from spacenote.core.modules.attachment.storage import (
    get_attachment_file_path,
    move_attachment_file,
    write_attachment_file,
)
from spacenote.core.modules.counter.models import CounterType
from spacenote.errors import NotFoundError, ValidationError

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
        space = self.core.services.space.get_space(space_id)
        number = await self.core.services.counter.get_next_sequence(space_id, CounterType.ATTACHMENT)

        note_number = None
        if note_id is not None:
            note = await self.core.services.note.get_note(note_id)
            note_number = note.number

        attachment = Attachment(
            space_id=space_id,
            note_id=note_id,
            user_id=user_id,
            number=number,
            filename=filename,
            size=len(content),
            mime_type=mime_type,
        )

        write_attachment_file(
            attachments_path=self.core.config.attachments_path,
            space_slug=space.slug,
            attachment_number=attachment.number,
            note_number=note_number,
            content=content,
        )

        await self._collection.insert_one(attachment.to_mongo())
        logger.debug("Created attachment", attachment_id=attachment.id, space_id=space_id, filename=filename)
        return attachment

    async def attach_to_note(self, attachment_id: UUID, note_id: UUID) -> None:
        """Attach a space-level attachment to a note by moving file and updating database.

        Args:
            attachment_id: The ID of the attachment to attach
            note_id: The note ID to attach to

        Raises:
            NotFoundError: If attachment or note not found
            ValidationError: If attachment already attached to another note or file not found
        """
        attachment = await self.get_attachment(attachment_id)

        if attachment.note_id is not None:
            raise ValidationError(f"Attachment {attachment_id} is already attached to note {attachment.note_id}")

        note = await self.core.services.note.get_note(note_id)
        space = self.core.services.space.get_space(attachment.space_id)

        try:
            old_path, new_path = move_attachment_file(
                attachments_path=self.core.config.attachments_path,
                space_slug=space.slug,
                attachment_number=attachment.number,
                old_note_number=None,
                new_note_number=note.number,
            )
            logger.debug("Moved attachment file", attachment_id=attachment_id, old_path=str(old_path), new_path=str(new_path))
        except FileNotFoundError as e:
            raise ValidationError(str(e)) from e

        await self._collection.update_one({"_id": attachment_id}, {"$set": {"note_id": note_id}})
        logger.debug("Attached attachment to note", attachment_id=attachment_id, note_id=note_id, note_number=note.number)

    async def get_attachment_file_info(self, attachment_id: UUID) -> AttachmentFileInfo:
        """Get file info for attachment download.

        Args:
            attachment_id: Attachment ID

        Returns:
            AttachmentFileInfo with file_path, filename, and mime_type

        Raises:
            NotFoundError: If attachment or file not found
        """
        attachment = await self.get_attachment(attachment_id)
        space = self.core.services.space.get_space(attachment.space_id)

        note_number = None
        if attachment.note_id is not None:
            note = await self.core.services.note.get_note(attachment.note_id)
            note_number = note.number

        file_path = get_attachment_file_path(
            attachments_path=self.core.config.attachments_path,
            space_slug=space.slug,
            attachment_number=attachment.number,
            note_number=note_number,
        )

        if not file_path.exists():
            raise NotFoundError(f"Attachment file not found: {attachment_id}")

        return AttachmentFileInfo(file_path=file_path, filename=attachment.filename, mime_type=attachment.mime_type)
