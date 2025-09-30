"""Notification message rendering for Telegram."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import structlog
from liquid import Environment

from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.telegram.models import NotificationContext, TelegramEventType
from spacenote.core.modules.user.models import User, UserView
from spacenote.errors import NotFoundError

logger = structlog.get_logger(__name__)


def render_notification_message(
    event_type: TelegramEventType,
    template: str,
    note: Note,
    space: Space,
    user: UserView,
    frontend_url: str,
    user_cache: Mapping[UUID, User],
    comment: Comment | None = None,
) -> str:
    """Render notification message from template with all data preparation.

    Args:
        event_type: Type of event (note_created, note_updated, comment_created)
        template: Liquid template string to render
        note: Note involved in the event
        space: Space where event occurred
        user: User who triggered the event
        frontend_url: Base URL for generating links
        user_cache: Read-only mapping of users (UUID -> User)
        comment: Comment object (required for COMMENT_CREATED events)

    Returns:
        Rendered message ready to send

    Raises:
        ValueError: If template rendering fails
    """
    # Generate URL based on event type
    if event_type == TelegramEventType.COMMENT_CREATED and comment:
        url = f"{frontend_url}/s/{space.slug}/notes/{note.number}#comment-{comment.number}"
    else:
        url = f"{frontend_url}/s/{space.slug}/notes/{note.number}"

    # Create context
    context = NotificationContext(note=note, user=user, space=space, url=url, comment=comment)

    # Prepare fields with formatting
    prepared_fields: dict[str, Any] = {}
    for field in space.fields:
        field_value = note.fields.get(field.id)
        if field_value is None:
            prepared_fields[field.id] = None
        elif field.type == FieldType.USER:
            # Format user field to username
            try:
                if isinstance(field_value, str):
                    user_id = UUID(field_value)
                elif isinstance(field_value, UUID):
                    user_id = field_value
                else:
                    prepared_fields[field.id] = str(field_value)
                    continue

                cached_user = user_cache.get(user_id)
                prepared_fields[field.id] = "👤" + cached_user.username if cached_user else str(field_value)
            except (ValueError, NotFoundError):
                prepared_fields[field.id] = str(field_value)
        elif field.type == FieldType.TAGS:
            # Format tags as comma-separated string
            prepared_fields[field.id] = ", ".join(field_value) if isinstance(field_value, list) else str(field_value)
        elif field.type == FieldType.BOOLEAN:
            # Format boolean as readable text
            prepared_fields[field.id] = "Yes" if field_value else "No"
        else:
            prepared_fields[field.id] = field_value

    # Prepare context dict and inject formatted fields
    context_dict = context.model_dump(mode="json")
    context_dict["note"]["fields"] = prepared_fields

    # Render template
    try:
        env = Environment()
        tmpl = env.from_string(template)
        return tmpl.render(**context_dict)
    except Exception as e:
        logger.exception("template_render_failed", error=str(e), template=template[:100])
        raise ValueError(f"Failed to render template: {e}") from e
