"""Service for managing IMAGE field type."""

import asyncio
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.attachment.storage import get_attachment_file_path
from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.core.modules.image.image import generate_image, get_image_path, is_valid_image
from spacenote.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class ImageService(Service):
    """Manages image generation for IMAGE field types."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._background_tasks: set[asyncio.Task[Any]] = set()

    def process_note_images(self, note_id: UUID) -> None:
        """Process IMAGE fields for a note: attach files and generate images.

        This method attaches IMAGE field attachments to the note and starts
        background tasks to generate images.

        Args:
            note_id: The note ID
        """
        task = asyncio.create_task(self._process_note_images_async(note_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _process_note_images_async(self, note_id: UUID) -> None:
        """Internal async implementation of process_note_images."""
        try:
            note = await self.core.services.note.get_note(note_id)
            space = self.core.services.space.get_space(note.space_id)

            image_tasks = []
            for field in space.fields:
                if field.type != FieldType.IMAGE:
                    continue

                attachment_id = note.fields.get(field.id)
                if attachment_id is None or not isinstance(attachment_id, UUID):
                    continue

                # Only attach if not already attached to this note (idempotent)
                attachment = await self.core.services.attachment.get_attachment(attachment_id)
                if attachment.note_id != note_id:
                    await self.core.services.attachment.attach_to_note(attachment_id, note_id)

                task = asyncio.create_task(self.generate_image(note_id, field.id, attachment_id))
                image_tasks.append(task)
        except Exception:
            logger.exception("Failed to process note images", note_id=note_id)

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

    async def generate_image(self, note_id: UUID, field_id: str, attachment_id: UUID) -> None:
        """Generate image for an IMAGE field attachment.

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

        await self._generate_image_for_field(note.number, field, attachment_id)

    async def _generate_image_for_field(self, note_number: int, field: SpaceField, attachment_id: UUID) -> None:
        """Generate image for a single IMAGE field.

        Args:
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

        # Get max_width from field options
        max_width = field.options.get(FieldOption.MAX_WIDTH)
        if not isinstance(max_width, int) or max_width <= 0:
            raise ValidationError(f"Invalid max_width for field '{field.id}': must be a positive integer")

        image_path = get_image_path(self.core.config.images_path, space.slug, note_number, field.id)

        # Skip if image already exists
        if image_path.exists():
            logger.debug("Image already exists, skipping", image_path=str(image_path), field_id=field.id)
            return

        try:
            width, height = generate_image(attachment_path, image_path, max_width)
            logger.info("Generated image", field_id=field.id, attachment_id=attachment_id, width=width, height=height)
        except Exception:
            logger.exception(
                "Failed to generate image",
                field_id=field.id,
                attachment_path=str(attachment_path),
                image_path=str(image_path),
            )

    async def get_image_path(self, space_id: UUID, note_number: int, field_id: str) -> Path:
        """Get file path for IMAGE field download.

        Args:
            space_id: Space ID
            note_number: Note number
            field_id: Field ID

        Returns:
            File path to image

        Raises:
            NotFoundError: If note, field, or image not found
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

        image_path = get_image_path(self.core.config.images_path, space.slug, note.number, field_id)

        if not image_path.exists():
            raise NotFoundError("Image not found")

        return image_path

    def delete_images_by_space(self, space_id: UUID) -> None:
        """Delete all images for a space from filesystem.

        Args:
            space_id: Space ID to delete images for
        """
        space = self.core.services.space.get_space(space_id)
        images_folder = Path(self.core.config.images_path) / space.slug

        if images_folder.exists():
            shutil.rmtree(images_folder)
            logger.debug("Deleted images folder", path=str(images_folder))
