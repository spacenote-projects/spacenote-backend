"""Service for managing image field previews."""

from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.core.modules.image.processor import generate_preview
from spacenote.core.modules.image.utils import get_preview_path
from spacenote.errors import ValidationError

logger = structlog.get_logger(__name__)


class ImageService(Service):
    """Manages image preview generation for IMAGE field types."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    async def generate_previews_for_note(self, space_id: UUID, note_number: int, field_values: dict[str, Any]) -> None:
        """Generate previews for all IMAGE fields in a note.

        Args:
            space_id: The space ID
            note_number: The note number within the space
            field_values: Dictionary of field_id -> field_value (parsed values)
        """
        space = self.core.services.space.get_space(space_id)

        for field in space.fields:
            if field.type != FieldType.IMAGE:
                continue

            field_value = field_values.get(field.id)
            if field_value is None:
                continue

            if not isinstance(field_value, UUID):
                logger.warning(
                    "Expected UUID for IMAGE field value",
                    field_id=field.id,
                    field_value=field_value,
                    type=type(field_value).__name__,
                )
                continue

            attachment_id = field_value

            try:
                await self._generate_previews_for_field(space_id, note_number, field, attachment_id)
            except Exception:
                logger.exception(
                    "Failed to generate previews for IMAGE field",
                    space_id=space_id,
                    note_number=note_number,
                    field_id=field.id,
                    attachment_id=attachment_id,
                )

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

        if not attachment.mime_type.startswith("image/"):
            raise ValidationError(f"Attachment {attachment_id} is not an image (mime_type: {attachment.mime_type})")

        # Get attachment file path
        attachments_path = self.core.config.attachments_path
        attachment_path = f"{attachments_path}/{attachment.get_storage_path(note_number)}"

        if not Path(attachment_path).exists():
            raise ValidationError(f"Attachment file not found: {attachment_path}")

        # Generate previews
        previews_config = field.options.get(FieldOption.PREVIEWS, {})
        if not isinstance(previews_config, dict):
            logger.warning("Invalid previews config", field_id=field.id, previews_config=previews_config)
            return

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
                width, height = generate_preview(attachment_path, preview_path, max_width)
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
                    attachment_path=attachment_path,
                    preview_path=preview_path,
                )
