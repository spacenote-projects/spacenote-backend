from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.telegram.models import TelegramEventType, TelegramIntegration, TelegramNotificationConfig
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
