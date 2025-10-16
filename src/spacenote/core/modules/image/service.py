"""Service for managing image field previews."""

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.attachment.storage import get_attachment_file_path
from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.core.modules.image.processor import generate_preview
from spacenote.core.modules.image.utils import get_preview_path, is_valid_image
from spacenote.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class ImageService(Service):
    """Manages image preview generation for IMAGE field types."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._background_tasks: set[asyncio.Task[Any]] = set()

    def process_note_images(self, note_id: UUID) -> None:
        """Process IMAGE fields for a note: attach files and generate previews.

        This method attaches IMAGE field attachments to the note and starts
        background tasks to generate previews.

        Args:
            note_id: The note ID
        """
        task = asyncio.create_task(self._process_note_images_async(note_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _process_note_images_async(self, note_id: UUID) -> None:
        """Internal async implementation of process_note_images."""
        note = await self.core.services.note.get_note(note_id)
        space = self.core.services.space.get_space(note.space_id)

        preview_tasks = []
        for field in space.fields:
            if field.type != FieldType.IMAGE:
                continue

            attachment_id = note.fields.get(field.id)
            if attachment_id is None or not isinstance(attachment_id, UUID):
                continue

            await self.core.services.attachment.attach_to_note(attachment_id, note_id)
            task = asyncio.create_task(self.generate_image_previews(note_id, field.id, attachment_id))
            preview_tasks.append(task)

    async def validate_image_attachment(self, attachment_id: UUID) -> None:
        """Validate that an attachment is a valid image file.

        This should be called BEFORE creating or updating a note to ensure the attachment is valid.

        Args:
            attachment_id: The attachment ID to validate

        Raises:
            NotFoundError: If attachment not found
            ValidationError: If attachment is not an image or file is invalid
        """
        attachment = await self.core.services.attachment.get_attachment(attachment_id)
        space = self.core.services.space.get_space(attachment.space_id)

        if not attachment.mime_type.startswith("image/"):
            raise ValidationError(f"Attachment {attachment_id} is not an image (mime_type: {attachment.mime_type})")

        file_path = get_attachment_file_path(
            attachments_path=self.core.config.attachments_path,
            space_slug=space.slug,
            attachment_number=attachment.number,
            note_number=None,
        )

        if not is_valid_image(file_path):
            raise ValidationError(f"Attachment {attachment_id} is not a valid image file")

    async def generate_image_previews(self, note_id: UUID, field_id: str, attachment_id: UUID) -> None:
        """Generate preview images for an IMAGE field attachment.

        Args:
            note_id: The note ID
            field_id: The field ID
            attachment_id: The attachment ID

        Raises:
            NotFoundError: If note or attachment not found
            ValidationError: If field not found, wrong type, or attachment invalid
        """
        note = await self.core.services.note.get_note(note_id)
        space = self.core.services.space.get_space(note.space_id)
        field = space.get_field(field_id)

        if field is None:
            raise ValidationError(f"Field '{field_id}' not found in space {note.space_id}")

        if field.type != FieldType.IMAGE:
            raise ValidationError(f"Field '{field_id}' is not IMAGE type (got {field.type})")

        await self._generate_previews_for_field(note.space_id, note.number, field, attachment_id)

    async def _generate_previews_for_field(
        self, space_id: UUID, note_number: int, field: SpaceField, attachment_id: UUID
    ) -> None:
        """Generate previews for a single IMAGE field.

        Args:
            space_id: The space ID
            note_number: The note number
            field: The field definition
            attachment_id: The attachment ID

        Raises:
            ValidationError: If attachment not found or is not an image
        """
        attachment = await self.core.services.attachment.get_attachment(attachment_id)
        space = self.core.services.space.get_space(attachment.space_id)

        if not attachment.mime_type.startswith("image/"):
            raise ValidationError(f"Attachment {attachment_id} is not an image (mime_type: {attachment.mime_type})")

        # Get attachment file path
        attachment_path = get_attachment_file_path(
            attachments_path=self.core.config.attachments_path,
            space_slug=space.slug,
            attachment_number=attachment.number,
            note_number=note_number,
        )

        if not attachment_path.exists():
            raise ValidationError(f"Attachment file not found: {attachment_path}")

        # Generate previews
        previews_config = field.options.get(FieldOption.PREVIEWS, {})
        if not isinstance(previews_config, dict):
            raise ValidationError(f"Invalid previews config for field '{field.id}': must be a dictionary")

        previews_base_path = self.core.config.previews_path

        for preview_key, preview_config in previews_config.items():
            if not isinstance(preview_config, dict):
                continue

            max_width = preview_config.get("max_width")
            if not isinstance(max_width, int) or max_width <= 0:
                continue

            preview_path = get_preview_path(previews_base_path, space_id, note_number, field.id, attachment_id, preview_key)

            # Skip if preview already exists
            if Path(preview_path).exists():
                logger.debug(
                    "Preview already exists, skipping",
                    preview_path=preview_path,
                    field_id=field.id,
                    preview_key=preview_key,
                )
                continue

            try:
                width, height = generate_preview(str(attachment_path), preview_path, max_width)
                logger.info(
                    "Generated preview",
                    field_id=field.id,
                    preview_key=preview_key,
                    attachment_id=attachment_id,
                    width=width,
                    height=height,
                )
            except Exception:
                logger.exception(
                    "Failed to generate preview",
                    field_id=field.id,
                    preview_key=preview_key,
                    attachment_path=str(attachment_path),
                    preview_path=preview_path,
                )

    async def get_image_preview_path(self, space_id: UUID, note_number: int, field_id: str, preview_key: str) -> str:
        """Get file path for preview image download.

        Args:
            space_id: Space ID
            note_number: Note number
            field_id: Field ID
            preview_key: Preview size key (e.g., "thumbnail", "medium")

        Returns:
            File path to preview image

        Raises:
            NotFoundError: If note, field, or preview not found
            ValidationError: If field is not IMAGE type or has no attachment
        """
        note = await self.core.services.note.get_note_by_number(space_id, note_number)
        space = self.core.services.space.get_space(space_id)

        field = space.get_field(field_id)
        if field is None:
            raise NotFoundError(f"Field '{field_id}' not found")

        if field.type != FieldType.IMAGE:
            raise ValidationError(f"Field '{field_id}' is not an IMAGE field")

        attachment_id = note.fields.get(field_id)
        if attachment_id is None or not isinstance(attachment_id, UUID):
            raise NotFoundError(f"Note {note_number} has no attachment for field '{field_id}'")

        preview_path = get_preview_path(
            self.core.config.previews_path, space_id, note.number, field_id, attachment_id, preview_key
        )

        if not Path(preview_path).exists():
            raise NotFoundError(f"Preview not found: {preview_key}")

        return preview_path
