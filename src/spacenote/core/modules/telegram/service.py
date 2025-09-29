from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.telegram.models import (
    CommentCreatedContext,
    NoteCreatedContext,
    NoteUpdatedContext,
    TelegramEventType,
    TelegramIntegration,
    TelegramNotificationConfig,
    TelegramTemplateContext,
)
from spacenote.core.modules.telegram.renderer import render_telegram_template
from spacenote.core.modules.telegram.sender import send_telegram_message
from spacenote.core.modules.telegram.test_data import (
    generate_comment_created_context,
    generate_note_created_context,
    generate_note_updated_context,
)
from spacenote.core.modules.telegram.utils import generate_comment_url, generate_note_url
from spacenote.core.modules.user.models import UserView
from spacenote.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class TelegramService(Service):
    """Service for managing Telegram integrations."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("telegram_integrations")

    async def on_start(self) -> None:
        await self._collection.create_index([("space_id", 1)], unique=True)
        logger.debug("telegram_service_started")

    def _prepare_fields_for_template(self, note: Note, space: Space) -> dict[str, Any]:
        """Prepare note fields for template rendering.

        Converts raw field values to display-friendly format:
        - USER fields: UUID -> username
        - DATETIME fields: ISO string -> formatted string
        - TAGS fields: list -> comma-separated string
        - Other fields: appropriate formatting

        Args:
            note: Note with raw field values
            space: Space with field definitions

        Returns:
            Dictionary with field_id -> formatted value mappings
        """
        prepared_fields: dict[str, Any] = {}

        for field in space.fields:
            field_value = note.fields.get(field.id)

            if field_value is None:
                prepared_fields[field.id] = None
                continue

            if field.type == FieldType.USER:
                # Resolve UUID to username
                try:
                    if isinstance(field_value, str):
                        user_id = UUID(field_value)
                    elif isinstance(field_value, UUID):
                        user_id = field_value
                    else:
                        prepared_fields[field.id] = str(field_value)
                        continue

                    user = self.core.services.user.get_user(user_id)
                    prepared_fields[field.id] = user.username
                except (ValueError, NotFoundError):
                    # If UUID is invalid or user not found, use the raw value
                    prepared_fields[field.id] = str(field_value)

            elif field.type == FieldType.TAGS:
                # Convert list to comma-separated string
                if isinstance(field_value, list):
                    prepared_fields[field.id] = ", ".join(field_value)
                else:
                    prepared_fields[field.id] = str(field_value)

            elif field.type == FieldType.DATETIME:
                # Format datetime for display
                if isinstance(field_value, str):
                    # Already a string (ISO format), could format it better here
                    prepared_fields[field.id] = field_value
                else:
                    prepared_fields[field.id] = str(field_value)

            elif field.type == FieldType.BOOLEAN:
                # Convert boolean to readable string
                prepared_fields[field.id] = "Yes" if field_value else "No"

            else:
                # For other types (STRING, MARKDOWN, INT, FLOAT, STRING_CHOICE), use as is
                prepared_fields[field.id] = field_value

        return prepared_fields

    def _prepare_context_for_template(self, context: TelegramTemplateContext) -> dict[str, Any]:
        """Prepare context for template rendering, including field preparation.

        Args:
            context: Template context with raw data

        Returns:
            Dictionary with prepared data for template rendering
        """
        # Convert context to dict
        context_dict = context.model_dump(mode="json")

        # Prepare fields for display if we have a note context
        if (
            isinstance(context, (NoteCreatedContext, NoteUpdatedContext, CommentCreatedContext))
            and hasattr(context, "note")
            and hasattr(context, "space")
        ):
            prepared_fields = self._prepare_fields_for_template(context.note, context.space)
            # Replace raw fields with prepared fields
            context_dict["note"]["fields"] = prepared_fields

        return context_dict

    async def get_telegram_integration(self, space_id: UUID) -> TelegramIntegration | None:
        """Get Telegram integration for a space."""
        doc = await self._collection.find_one({"space_id": space_id})
        if doc is None:
            return None
        return TelegramIntegration.model_validate(doc)

    async def create_telegram_integration(self, space_id: UUID, bot_token: str, chat_id: str) -> TelegramIntegration:
        """Create a new Telegram integration for a space."""
        existing = await self.get_telegram_integration(space_id)
        if existing:
            raise ValidationError(f"Telegram integration already exists for space {space_id}")

        integration = TelegramIntegration(
            space_id=space_id,
            bot_token=bot_token,
            chat_id=chat_id,
        )

        await self._collection.insert_one(integration.to_mongo())
        logger.info("telegram_integration_created", space_id=space_id)
        return integration

    async def update_telegram_integration(
        self,
        space_id: UUID,
        bot_token: str | None = None,
        chat_id: str | None = None,
        is_enabled: bool | None = None,
    ) -> TelegramIntegration:
        """Update an existing Telegram integration for a space.

        Parameters are optional (None) to support partial updates - only fields
        provided will be updated, while None values are ignored."""
        integration = await self.get_telegram_integration(space_id)
        if not integration:
            raise ValidationError(f"Telegram integration not found for space {space_id}")

        update_data: dict[str, Any] = {}
        if bot_token is not None:
            update_data["bot_token"] = bot_token
        if chat_id is not None:
            update_data["chat_id"] = chat_id
        if is_enabled is not None:
            update_data["is_enabled"] = is_enabled

        if update_data:
            await self._collection.update_one({"space_id": space_id}, {"$set": update_data})
            logger.info("telegram_integration_updated", space_id=space_id, fields=list(update_data.keys()))

            # Refresh the integration to return updated data
            integration = await self.get_telegram_integration(space_id)
            if not integration:
                raise ValidationError(f"Failed to retrieve updated integration for space {space_id}")

        return integration

    async def delete_telegram_integration(self, space_id: UUID) -> None:
        """Delete a Telegram integration for a space."""
        result = await self._collection.delete_one({"space_id": space_id})
        if result.deleted_count == 0:
            raise ValidationError(f"Telegram integration not found for space {space_id}")
        logger.info("telegram_integration_deleted", space_id=space_id)

    async def update_notification_config(
        self,
        space_id: UUID,
        event_type: TelegramEventType,
        enabled: bool,
        template: str,
    ) -> TelegramNotificationConfig:
        """Update notification configuration for a specific event type."""
        integration = await self.get_telegram_integration(space_id)
        if not integration:
            raise ValidationError(f"Telegram integration not found for space {space_id}")

        # Update the specific notification config
        await self._collection.update_one(
            {"space_id": space_id}, {"$set": {f"notifications.{event_type}": {"enabled": enabled, "template": template}}}
        )

        logger.info("telegram_notification_updated", space_id=space_id, event_type=event_type)

        # Return the updated notification config
        return TelegramNotificationConfig(enabled=enabled, template=template)

    async def send_test_message(self, space_id: UUID) -> dict[TelegramEventType, str | None]:
        """Send test messages for all enabled notification types.

        Tests each enabled event type by generating mock data, rendering
        the configured template, and sending the message to Telegram.

        Returns:
            Dictionary mapping event types to error messages (None if successful)

        Raises:
            ValidationError: If no notifications are enabled or integration doesn't exist
        """
        integration = await self.get_telegram_integration(space_id)
        if not integration:
            raise ValidationError(f"Telegram integration not found for space {space_id}")

        if not integration.is_enabled:
            raise ValidationError("Telegram integration is disabled")

        # Check if at least one notification is enabled
        enabled_events = [event_type for event_type, config in integration.notifications.items() if config.enabled]
        if not enabled_events:
            raise ValidationError("All notification events are disabled")

        # Get space for generating mock data
        space = self.core.services.space.get_space(space_id)
        if not space:
            raise ValidationError(f"Space not found: {space_id}")

        results: dict[TelegramEventType, str | None] = {}

        # Test each enabled notification type
        for event_type in enabled_events:
            config = integration.notifications[event_type]

            try:
                # Generate appropriate mock context for the event type
                context: TelegramTemplateContext
                if event_type == TelegramEventType.NOTE_CREATED:
                    context = generate_note_created_context(space)
                elif event_type == TelegramEventType.NOTE_UPDATED:
                    context = generate_note_updated_context(space)
                elif event_type == TelegramEventType.COMMENT_CREATED:
                    context = generate_comment_created_context(space)
                else:
                    results[event_type] = f"Unknown event type: {event_type}"
                    continue

                # Render the template with mock data
                try:
                    prepared_context = self._prepare_context_for_template(context)
                    rendered_message = render_telegram_template(config.template, prepared_context)
                except Exception as e:
                    results[event_type] = f"Template render error: {e!s}"
                    continue

                # Add test header to the message
                test_header = f"🧪 <b>TEST: {event_type.upper()}</b>\n\n"
                full_message = test_header + rendered_message

                # Send the test message
                success, error_msg = await send_telegram_message(
                    integration.bot_token,
                    integration.chat_id,
                    full_message,
                    parse_mode="HTML",
                )

                results[event_type] = None if success else error_msg

            except Exception as e:
                results[event_type] = str(e)
                logger.exception(
                    "test_message_failed",
                    space_id=space_id,
                    event_type=event_type,
                    error=str(e),
                )

        logger.info(
            "test_messages_sent",
            space_id=space_id,
            tested_count=len(results),
            errors=[event_type for event_type, error in results.items() if error],
        )

        return results

    async def send_note_created_notification(
        self,
        note: Note,
        user_id: UUID,
        space_id: UUID,
    ) -> None:
        """Send notification when a note is created.

        This is a fire-and-forget operation that logs errors but doesn't
        raise exceptions to avoid disrupting the main operation.

        Args:
            note: The created note
            user_id: ID of the user who created the note
            space_id: ID of the space containing the note
        """
        try:
            # Get integration for the space
            integration = await self.get_telegram_integration(space_id)
            if not integration or not integration.is_enabled:
                return

            # Check if note_created notifications are enabled
            event_config = integration.notifications.get(TelegramEventType.NOTE_CREATED)
            if not event_config or not event_config.enabled:
                return

            # Get space and user for context
            space = self.core.services.space.get_space(space_id)
            if not space:
                logger.warning("space_not_found_for_notification", space_id=space_id)
                return

            user = self.core.services.user.get_user(user_id)
            if not user:
                logger.warning("user_not_found_for_notification", user_id=user_id)
                return

            # Generate note URL
            frontend_url = self.core.config.frontend_url
            note_url = generate_note_url(frontend_url, space.slug, note.number)

            # Create context for template
            context = NoteCreatedContext(
                note=note,
                user=UserView.from_domain(user),
                space=space,
                url=note_url,
            )

            # Prepare and render template
            prepared_context = self._prepare_context_for_template(context)
            rendered_message = render_telegram_template(event_config.template, prepared_context)

            # Send the notification
            success, error_msg = await send_telegram_message(
                integration.bot_token,
                integration.chat_id,
                rendered_message,
                parse_mode="HTML",
            )

            if success:
                logger.info(
                    "note_created_notification_sent",
                    space_id=space_id,
                    note_id=note.id,
                    note_number=note.number,
                )
            else:
                logger.warning(
                    "note_created_notification_failed",
                    space_id=space_id,
                    note_id=note.id,
                    error=error_msg,
                )

        except Exception as e:
            # Log error but don't propagate - notifications should never fail main operations
            logger.exception(
                "note_created_notification_error",
                space_id=space_id,
                note_id=note.id,
                error=str(e),
            )

    async def send_note_updated_notification(
        self,
        note: Note,
        user_id: UUID,
        space_id: UUID,
    ) -> None:
        """Send notification when a note is updated.

        This is a fire-and-forget operation that logs errors but doesn't
        raise exceptions to avoid disrupting the main operation.

        Args:
            note: The updated note
            user_id: ID of the user who updated the note
            space_id: ID of the space containing the note
        """
        try:
            # Get integration for the space
            integration = await self.get_telegram_integration(space_id)
            if not integration or not integration.is_enabled:
                return

            # Check if note_updated notifications are enabled
            event_config = integration.notifications.get(TelegramEventType.NOTE_UPDATED)
            if not event_config or not event_config.enabled:
                return

            # Get space and user for context
            space = self.core.services.space.get_space(space_id)
            if not space:
                logger.warning("space_not_found_for_notification", space_id=space_id)
                return

            user = self.core.services.user.get_user(user_id)
            if not user:
                logger.warning("user_not_found_for_notification", user_id=user_id)
                return

            # Generate note URL
            frontend_url = self.core.config.frontend_url
            note_url = generate_note_url(frontend_url, space.slug, note.number)

            # Create context for template
            context = NoteUpdatedContext(
                note=note,
                user=UserView.from_domain(user),
                space=space,
                url=note_url,
            )

            # Prepare and render template
            prepared_context = self._prepare_context_for_template(context)
            rendered_message = render_telegram_template(event_config.template, prepared_context)

            # Send the notification
            success, error_msg = await send_telegram_message(
                integration.bot_token,
                integration.chat_id,
                rendered_message,
                parse_mode="HTML",
            )

            if success:
                logger.info(
                    "note_updated_notification_sent",
                    space_id=space_id,
                    note_id=note.id,
                    note_number=note.number,
                )
            else:
                logger.warning(
                    "note_updated_notification_failed",
                    space_id=space_id,
                    note_id=note.id,
                    error=error_msg,
                )

        except Exception as e:
            # Log error but don't propagate - notifications should never fail main operations
            logger.exception(
                "note_updated_notification_error",
                space_id=space_id,
                note_id=note.id,
                error=str(e),
            )

    async def send_comment_created_notification(
        self,
        comment: Comment,
        note: Note,
        user_id: UUID,
        space_id: UUID,
    ) -> None:
        """Send notification when a comment is created.

        This is a fire-and-forget operation that logs errors but doesn't
        raise exceptions to avoid disrupting the main operation.

        Args:
            comment: The created comment
            note: The note containing the comment
            user_id: ID of the user who created the comment
            space_id: ID of the space containing the note
        """
        try:
            # Get integration for the space
            integration = await self.get_telegram_integration(space_id)
            if not integration or not integration.is_enabled:
                return

            # Check if comment_created notifications are enabled
            event_config = integration.notifications.get(TelegramEventType.COMMENT_CREATED)
            if not event_config or not event_config.enabled:
                return

            # Get space and user for context
            space = self.core.services.space.get_space(space_id)
            if not space:
                logger.warning("space_not_found_for_notification", space_id=space_id)
                return

            user = self.core.services.user.get_user(user_id)
            if not user:
                logger.warning("user_not_found_for_notification", user_id=user_id)
                return

            # Generate comment URL
            frontend_url = self.core.config.frontend_url
            comment_url = generate_comment_url(frontend_url, space.slug, note.number, comment.number)

            # Create context for template
            context = CommentCreatedContext(
                note=note,
                comment=comment,
                user=UserView.from_domain(user),
                space=space,
                url=comment_url,
            )

            # Prepare and render template
            prepared_context = self._prepare_context_for_template(context)
            rendered_message = render_telegram_template(event_config.template, prepared_context)

            # Send the notification
            success, error_msg = await send_telegram_message(
                integration.bot_token,
                integration.chat_id,
                rendered_message,
                parse_mode="HTML",
            )

            if success:
                logger.info(
                    "comment_created_notification_sent",
                    space_id=space_id,
                    note_id=note.id,
                    comment_id=comment.id,
                )
            else:
                logger.warning(
                    "comment_created_notification_failed",
                    space_id=space_id,
                    note_id=note.id,
                    comment_id=comment.id,
                    error=error_msg,
                )

        except Exception as e:
            # Log error but don't propagate - notifications should never fail main operations
            logger.exception(
                "comment_created_notification_error",
                space_id=space_id,
                note_id=note.id if note else None,
                comment_id=comment.id if comment else None,
                error=str(e),
            )
