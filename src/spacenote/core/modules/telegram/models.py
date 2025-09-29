"""Telegram integration models for space notifications."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel


class TelegramEventType(StrEnum):
    """Events that can trigger Telegram notifications.

    Supported events:
    - NOTE_CREATED: When a new note is created in the space
    - NOTE_UPDATED: When an existing note's fields are modified
    - COMMENT_CREATED: When a comment is added to a note
    """

    NOTE_CREATED = "note_created"
    NOTE_UPDATED = "note_updated"
    COMMENT_CREATED = "comment_created"


class TelegramNotificationConfig(BaseModel):
    """Configuration for a specific notification type.

    Each event type can be individually enabled/disabled and
    have its own Liquid template for message formatting.
    """

    enabled: bool = Field(True, description="Whether this notification type is enabled")
    template: str = Field(..., description="Liquid template for formatting the notification message")


# Default templates for each event type
NOTE_CREATED_DEFAULT_TEMPLATE = (
    "📝 <b>New note #{{note.number}}</b> in {{space.title}}\n"
    "{% for field_id, value in note.fields %}"
    "{% if value %}• {{field_id}}: {{value | truncate: 100}}\n{% endif %}"
    "{% endfor %}"
    "👤 {{user.username}}\n"
    "🔗 {{url}}"
)

NOTE_UPDATED_DEFAULT_TEMPLATE = (
    "✏️ <b>Note #{{note.number}} updated</b> in {{space.title}}\n"
    "{% for field_id, value in note.fields %}"
    "{% if value %}• {{field_id}}: {{value | truncate: 100}}\n{% endif %}"
    "{% endfor %}"
    "👤 {{user.username}}\n"
    "🔗 {{url}}"
)

COMMENT_CREATED_DEFAULT_TEMPLATE = (
    "💬 <b>New comment on note #{{note.number}}</b>\n👤 {{user.username}}: {{comment.content | truncate: 200}}\n🔗 {{url}}"
)


def get_default_notifications() -> dict[TelegramEventType, TelegramNotificationConfig]:
    """Get default notification configurations for all event types."""
    return {
        TelegramEventType.NOTE_CREATED: TelegramNotificationConfig(
            enabled=True,
            template=NOTE_CREATED_DEFAULT_TEMPLATE,
        ),
        TelegramEventType.NOTE_UPDATED: TelegramNotificationConfig(
            enabled=True,
            template=NOTE_UPDATED_DEFAULT_TEMPLATE,
        ),
        TelegramEventType.COMMENT_CREATED: TelegramNotificationConfig(
            enabled=True,
            template=COMMENT_CREATED_DEFAULT_TEMPLATE,
        ),
    }


class TelegramIntegration(MongoModel):
    """Telegram bot integration configuration for a space.

    Enables automatic notifications to a Telegram chat (channel, group, or direct message)
    when events occur in a space. Each space can have one Telegram integration.

    Template Variables:
    - {{user.username}} - Username of the person who triggered the event
    - {{note.number}} - Note number (e.g., 42)
    - {{note.fields.FIELD_ID}} - Any note field value (e.g., {{note.fields.title}})
    - {{comment.content}} - Comment text (for comment events)
    - {{comment.number}} - Comment number within the note
    - {{space.title}} - Name of the space
    - {{space.slug}} - URL slug of the space
    - {{url}} - Direct link to the note in the web interface

    Liquid Filters:
    - truncate: Limit text length (e.g., {{comment.content | truncate: 100}})
    - escape: HTML escape text for safe display
    - date: Format dates (e.g., {{note.created_at | date: '%Y-%m-%d'}})
    - upcase/downcase: Change text case
    """

    space_id: UUID = Field(..., description="ID of the space this integration belongs to")
    bot_token: str = Field(..., description="Telegram Bot API token (keep secure!)")
    chat_id: str = Field(..., description="Telegram chat ID (can be numeric ID or @username for public channels)")
    is_enabled: bool = Field(True, description="Global on/off switch for all notifications")
    notifications: dict[TelegramEventType, TelegramNotificationConfig] = Field(
        default_factory=get_default_notifications, description="Notification configuration for each event type"
    )
