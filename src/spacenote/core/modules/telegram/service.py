from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.telegram.models import (
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
from spacenote.errors import ValidationError

logger = structlog.get_logger(__name__)


class TelegramService(Service):
    """Service for managing Telegram integrations."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("telegram_integrations")

    async def on_start(self) -> None:
        await self._collection.create_index([("space_id", 1)], unique=True)
        logger.debug("telegram_service_started")

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
                    rendered_message = render_telegram_template(config.template, context)
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
