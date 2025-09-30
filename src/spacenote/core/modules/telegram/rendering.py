"""Notification message rendering for Telegram."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import structlog
from liquid import Environment

from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.field.models import FieldType, FieldValueType
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.telegram.models import NotificationContext, TelegramEventType
from spacenote.core.modules.user.models import User, UserView
from spacenote.errors import NotFoundError

logger = structlog.get_logger(__name__)


def _format_field_value(field_value: FieldValueType, field_type: FieldType, user_cache: Mapping[UUID, User]) -> FieldValueType:
    """Format a field value for display in notification templates.

    Args:
        field_value: The raw field value
        field_type: The type of the field
        user_cache: Read-only mapping of users

    Returns:
        Formatted field value
    """
    if field_value is None:
        return None

    if field_type == FieldType.USER:
        try:
            if isinstance(field_value, str):
                user_id = UUID(field_value)
            elif isinstance(field_value, UUID):
                user_id = field_value
            else:
                return str(field_value)

            cached_user = user_cache.get(user_id)
            return "👤" + cached_user.username if cached_user else str(field_value)
        except (ValueError, NotFoundError):
            return str(field_value)
    elif field_type == FieldType.TAGS:
        return ", ".join(field_value) if isinstance(field_value, list) else str(field_value)
    elif field_type == FieldType.BOOLEAN:
        return "Yes" if field_value else "No"
    else:
        return field_value


def render_notification_message(
    event_type: TelegramEventType,
    template: str,
    note: Note,
    space: Space,
    user: UserView,
    frontend_url: str,
    user_cache: Mapping[UUID, User],
    comment: Comment | None = None,
    updated_fields: dict[str, Any] | None = None,
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
        updated_fields: Dictionary of updated fields (only for NOTE_UPDATED events)

    Returns:
        Rendered message ready to send

    Raises:
        ValueError: If template rendering fails
    """
    # Generate URL based on event type
    if event_type == TelegramEventType.COMMENT_CREATED and comment:
        url = f"{frontend_url}/s/{space.slug}/{note.number}#comment-{comment.number}"
    else:
        url = f"{frontend_url}/s/{space.slug}/{note.number}"

    # Create context
    context = NotificationContext(note=note, user=user, space=space, url=url, comment=comment, updated_fields=updated_fields)

    # Prepare fields with formatting
    prepared_fields: dict[str, Any] = {}
    for field in space.fields:
        field_value = note.fields.get(field.id)
        prepared_fields[field.id] = _format_field_value(field_value, field.type, user_cache)

    # Prepare updated_fields with formatting (if provided)
    prepared_updated_fields: dict[str, Any] | None = None
    if updated_fields is not None:
        prepared_updated_fields = {}
        field_map = {field.id: field for field in space.fields}
        for field_id, field_value in updated_fields.items():
            field_def = field_map.get(field_id)
            if field_def is not None:
                prepared_updated_fields[field_id] = _format_field_value(field_value, field_def.type, user_cache)
            else:
                prepared_updated_fields[field_id] = field_value

    # Prepare context dict and inject formatted fields
    context_dict = context.model_dump(mode="json")
    context_dict["note"]["fields"] = prepared_fields
    if prepared_updated_fields is not None:
        context_dict["note"]["updated_fields"] = prepared_updated_fields

    # Render template
    try:
        env = Environment()
        tmpl = env.from_string(template)
        return tmpl.render(**context_dict)
    except Exception as e:
        logger.exception("template_render_failed", error=str(e), template=template[:100])
        raise ValueError(f"Failed to render template: {e}") from e
