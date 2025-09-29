import asyncio
from typing import Any
from uuid import UUID

import structlog
from liquid import Environment
from pymongo.asynchronous.database import AsyncDatabase
from telegram import Bot
from telegram.error import TelegramError

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
from spacenote.core.modules.telegram.test_data import generate_test_context
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
        self._notification_tasks: set[asyncio.Task[None]] = set()
        logger.debug("telegram_service_started")

    def _format_user_field(self, value: Any) -> str:  # noqa: ANN401
        """Format user field value to username."""
        try:
            if isinstance(value, str):
                user_id = UUID(value)
            elif isinstance(value, UUID):
                user_id = value
            else:
                return str(value)
            user = self.core.services.user.get_user(user_id)
        except (ValueError, NotFoundError):
            return str(value)
        else:
            return user.username

    def _format_tags_field(self, value: Any) -> str:  # noqa: ANN401
        """Format tags field as comma-separated string."""
        return ", ".join(value) if isinstance(value, list) else str(value)

    def _format_boolean_field(self, value: Any) -> str:  # noqa: ANN401
        """Format boolean field as readable text."""
        return "Yes" if value else "No"

    def _prepare_fields_for_template(self, note: Note, space: Space) -> dict[str, Any]:
        """Prepare note fields for template rendering."""
        field_formatters = {
            FieldType.USER: self._format_user_field,
            FieldType.TAGS: self._format_tags_field,
            FieldType.BOOLEAN: self._format_boolean_field,
        }

        prepared_fields: dict[str, Any] = {}
        for field in space.fields:
            field_value = note.fields.get(field.id)
            if field_value is None:
                prepared_fields[field.id] = None
            else:
                formatter = field_formatters.get(field.type)
                prepared_fields[field.id] = formatter(field_value) if formatter else field_value

        return prepared_fields

    def _prepare_context_for_template(self, context: TelegramTemplateContext) -> dict[str, Any]:
        """Prepare context for template rendering, including field preparation."""
        context_dict = context.model_dump(mode="json")

        if (
            isinstance(context, (NoteCreatedContext, NoteUpdatedContext, CommentCreatedContext))
            and hasattr(context, "note")
            and hasattr(context, "space")
        ):
            prepared_fields = self._prepare_fields_for_template(context.note, context.space)
            context_dict["note"]["fields"] = prepared_fields

        return context_dict

    def _render_template(self, template: str, context: dict[str, Any]) -> str:
        """Render a Liquid template with the given context."""
        try:
            env = Environment()
            tmpl = env.from_string(template)
            return tmpl.render(**context)
        except Exception as e:
            logger.exception("template_render_failed", error=str(e), template=template[:100])
            raise ValueError(f"Failed to render template: {e}") from e

    async def _send_telegram_message(
        self, bot_token: str, chat_id: str, text: str, parse_mode: str | None = None
    ) -> tuple[bool, str | None]:
        """Send a text message to Telegram."""
        try:
            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        except TelegramError as e:
            error_msg = str(e)
            logger.exception("telegram_send_failed", chat_id=chat_id, error=error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.exception("telegram_send_error", chat_id=chat_id, error=error_msg)
            return False, error_msg
        else:
            logger.info("telegram_message_sent", chat_id=chat_id, parse_mode=parse_mode)
            return True, None

    def _generate_note_url(self, space_slug: str, note_number: int) -> str:
        """Generate a direct URL to a note in the frontend."""
        frontend_url = self.core.config.frontend_url
        return f"{frontend_url}/s/{space_slug}/notes/{note_number}"

    def _generate_comment_url(self, space_slug: str, note_number: int, comment_number: int) -> str:
        """Generate a direct URL to a comment in the frontend."""
        frontend_url = self.core.config.frontend_url
        return f"{frontend_url}/s/{space_slug}/notes/{note_number}#comment-{comment_number}"

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

    def _create_notification_context(
        self,
        event_type: TelegramEventType,
        space: Space,
        user: UserView,
        note: Note,
        comment: Comment | None = None,
    ) -> TelegramTemplateContext:
        """Create the appropriate context for a notification event."""
        if event_type == TelegramEventType.NOTE_CREATED:
            url = self._generate_note_url(space.slug, note.number)
            return NoteCreatedContext(note=note, user=user, space=space, url=url)

        if event_type == TelegramEventType.NOTE_UPDATED:
            url = self._generate_note_url(space.slug, note.number)
            return NoteUpdatedContext(note=note, user=user, space=space, url=url)

        if event_type == TelegramEventType.COMMENT_CREATED:
            if not comment:
                raise ValueError("Comment is required for COMMENT_CREATED event")
            url = self._generate_comment_url(space.slug, note.number, comment.number)
            return CommentCreatedContext(note=note, comment=comment, user=user, space=space, url=url)

        raise ValueError(f"Unknown event type: {event_type}")

    async def _send_notification_async(
        self,
        event_type: TelegramEventType,
        space_id: UUID,
        user_id: UUID,
        note: Note,
        comment: Comment | None = None,
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

            context = self._create_notification_context(event_type, space, UserView.from_domain(user), note, comment)

            prepared_context = self._prepare_context_for_template(context)
            rendered_message = self._render_template(event_config.template, prepared_context)

            success, error_msg = await self._send_telegram_message(
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

    def send_note_created_notification(self, note: Note, user_id: UUID, space_id: UUID) -> None:
        """Send notification when a note is created."""
        task = asyncio.create_task(self._send_notification_async(TelegramEventType.NOTE_CREATED, space_id, user_id, note))
        self._notification_tasks.add(task)
        task.add_done_callback(self._notification_tasks.discard)

    def send_note_updated_notification(self, note: Note, user_id: UUID, space_id: UUID) -> None:
        """Send notification when a note is updated."""
        task = asyncio.create_task(self._send_notification_async(TelegramEventType.NOTE_UPDATED, space_id, user_id, note))
        self._notification_tasks.add(task)
        task.add_done_callback(self._notification_tasks.discard)

    def send_comment_created_notification(self, comment: Comment, note: Note, user_id: UUID, space_id: UUID) -> None:
        """Send notification when a comment is created."""
        task = asyncio.create_task(
            self._send_notification_async(TelegramEventType.COMMENT_CREATED, space_id, user_id, note, comment)
        )
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
                    prepared_context = self._prepare_context_for_template(context)
                    rendered_message = self._render_template(config.template, prepared_context)
                except Exception as e:
                    results[event_type] = f"Template render error: {e!s}"
                    continue

                test_header = f"🧪 <b>TEST: {event_type.upper()}</b>\n\n"
                full_message = test_header + rendered_message

                success, error_msg = await self._send_telegram_message(
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
