import asyncio
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.telegram.models import (
    TelegramEventType,
    TelegramIntegration,
    TelegramNotificationConfig,
)
from spacenote.core.modules.telegram.rendering import render_notification_message
from spacenote.core.modules.telegram.sender import send_telegram_message
from spacenote.core.modules.telegram.test_data import generate_test_context
from spacenote.core.modules.user.models import UserView
from spacenote.errors import ValidationError

logger = structlog.get_logger(__name__)


class TelegramService(Service):
    """Service for managing Telegram integrations."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("telegram_integrations")

    async def on_start(self) -> None:
        await self._collection.create_index([("space_id", 1)], unique=True)
        self._notification_tasks: set[asyncio.Task[None]] = set()
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
        """Update an existing Telegram integration for a space."""
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

        await self._collection.update_one(
            {"space_id": space_id}, {"$set": {f"notifications.{event_type}": {"enabled": enabled, "template": template}}}
        )

        logger.info("telegram_notification_updated", space_id=space_id, event_type=event_type)
        return TelegramNotificationConfig(enabled=enabled, template=template)

    async def _send_notification_async(
        self,
        event_type: TelegramEventType,
        space_id: UUID,
        user_id: UUID,
        note: Note,
        comment: Comment | None = None,
        updated_fields: dict[str, Any] | None = None,
    ) -> None:
        """Internal async method to send any type of notification."""
        try:
            integration = await self.get_telegram_integration(space_id)
            if not integration or not integration.is_enabled:
                return

            event_config = integration.notifications.get(event_type)
            if not event_config or not event_config.enabled:
                return

            space = self.core.services.space.get_space(space_id)
            if not space:
                logger.warning("space_not_found_for_notification", space_id=space_id)
                return

            user = self.core.services.user.get_user(user_id)
            if not user:
                logger.warning("user_not_found_for_notification", user_id=user_id)
                return

            # Render notification message
            rendered_message = render_notification_message(
                event_type=event_type,
                template=event_config.template,
                note=note,
                space=space,
                user=UserView.from_domain(user),
                frontend_url=self.core.config.frontend_url,
                user_cache=self.core.services.user.get_user_cache(),
                comment=comment,
                updated_fields=updated_fields,
            )

            success, error_msg = await send_telegram_message(
                integration.bot_token,
                integration.chat_id,
                rendered_message,
                parse_mode="HTML",
            )

            if success:
                logger.info(
                    "notification_sent",
                    event_type=event_type,
                    space_id=space_id,
                    note_id=note.id,
                    comment_id=comment.id if comment else None,
                )
            else:
                logger.warning(
                    "notification_failed",
                    event_type=event_type,
                    space_id=space_id,
                    note_id=note.id,
                    error=error_msg,
                )

        except Exception as e:
            logger.exception(
                "notification_error",
                event_type=event_type,
                space_id=space_id,
                note_id=note.id,
                error=str(e),
            )

    def send_notification(
        self,
        event_type: TelegramEventType,
        note: Note,
        user_id: UUID,
        space_id: UUID,
        comment: Comment | None = None,
        updated_fields: dict[str, Any] | None = None,
    ) -> None:
        """Send notification for any event type in the background.

        Args:
            event_type: Type of event (note_created, note_updated, comment_created)
            note: Note involved in the event
            user_id: User who triggered the event
            space_id: Space where event occurred
            comment: Comment object (required for COMMENT_CREATED events)
            updated_fields: Dictionary of updated fields (only for NOTE_UPDATED events)
        """
        task = asyncio.create_task(self._send_notification_async(event_type, space_id, user_id, note, comment, updated_fields))
        self._notification_tasks.add(task)
        task.add_done_callback(self._notification_tasks.discard)

    async def send_test_message(self, space_id: UUID) -> dict[TelegramEventType, str | None]:
        """Send test messages for all enabled notification types."""

        integration = await self.get_telegram_integration(space_id)
        if not integration:
            raise ValidationError(f"Telegram integration not found for space {space_id}")

        if not integration.is_enabled:
            raise ValidationError("Telegram integration is disabled")

        enabled_events = [event_type for event_type, config in integration.notifications.items() if config.enabled]
        if not enabled_events:
            raise ValidationError("All notification events are disabled")

        space = self.core.services.space.get_space(space_id)
        if not space:
            raise ValidationError(f"Space not found: {space_id}")

        results: dict[TelegramEventType, str | None] = {}

        for event_type in enabled_events:
            config = integration.notifications[event_type]

            try:
                context = generate_test_context(event_type, space)

                try:
                    rendered_message = render_notification_message(
                        event_type=event_type,
                        template=config.template,
                        note=context.note,
                        space=space,
                        user=context.user,
                        frontend_url=self.core.config.frontend_url,
                        user_cache=self.core.services.user.get_user_cache(),
                        comment=context.comment if hasattr(context, "comment") else None,
                        updated_fields=context.updated_fields if hasattr(context, "updated_fields") else None,
                    )
                except Exception as e:
                    results[event_type] = f"Template render error: {e!s}"
                    continue

                test_header = f"🧪 <b>TEST: {event_type.upper()}</b>\n\n"
                full_message = test_header + rendered_message

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
