from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.telegram.models import TelegramIntegration
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
