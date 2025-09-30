"""Mock data generator for testing Telegram notifications."""

import random
from uuid import uuid4

from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.field.models import FieldOption, FieldType, FieldValueType
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.telegram.models import NotificationContext, TelegramEventType
from spacenote.core.modules.user.models import UserView
from spacenote.utils import now


def _generate_mock_note_fields(space: Space) -> dict[str, FieldValueType]:
    """Generate mock field values based on space field definitions."""
    mock_fields: dict[str, FieldValueType] = {}

    for field in space.fields:
        if field.type == FieldType.STRING:
            mock_fields[field.id] = f"Test {field.id}"
        elif field.type == FieldType.MARKDOWN:
            mock_fields[field.id] = f"# Test {field.id}\n\nSample markdown content"
        elif field.type == FieldType.BOOLEAN:
            mock_fields[field.id] = True
        elif field.type == FieldType.STRING_CHOICE:
            values = field.options.get(FieldOption.VALUES, [])
            if values and isinstance(values, list):
                mock_fields[field.id] = values[0]
        elif field.type == FieldType.TAGS:
            mock_fields[field.id] = ["tag1", "tag2"]
        elif field.type == FieldType.USER:
            if space.members:
                mock_fields[field.id] = str(random.choice(list(space.members)))
            else:
                mock_fields[field.id] = str(uuid4())
        elif field.type == FieldType.DATETIME:
            mock_fields[field.id] = now().isoformat()
        elif field.type == FieldType.INT:
            mock_fields[field.id] = 42
        elif field.type == FieldType.FLOAT:
            mock_fields[field.id] = 3.14

    return mock_fields


def generate_test_context(event_type: TelegramEventType, space: Space) -> NotificationContext:
    """Generate test context for any notification event type.

    Args:
        event_type: Type of notification event to generate context for
        space: Space configuration

    Returns:
        Template context with mock data for the specified event type
    """
    mock_fields = _generate_mock_note_fields(space)
    test_time = now()
    user_id = random.choice(list(space.members)) if space.members else uuid4()
    note_id = uuid4()

    # Create common mock objects
    note = Note(
        id=note_id,
        space_id=space.id,
        number=9999,
        user_id=user_id,
        fields=mock_fields,
        created_at=test_time,
        edited_at=test_time if event_type == TelegramEventType.NOTE_UPDATED else None,
        activity_at=test_time,
    )

    user = UserView(id=user_id, username="test_user")

    # Generate URL, comment, and updated_fields based on event type
    comment = None
    updated_fields = None

    if event_type == TelegramEventType.COMMENT_CREATED:
        comment = Comment(
            id=uuid4(),
            note_id=note_id,
            space_id=space.id,
            user_id=user_id,
            number=1,
            content="This is a test comment for notification testing. "
            "It demonstrates how your comment notifications will appear.",
            created_at=test_time,
        )
        url = f"https://spacenote.app/s/{space.slug}/notes/9999#comment-1"
    elif event_type == TelegramEventType.NOTE_UPDATED:
        # For NOTE_UPDATED, generate a subset of fields as updated_fields
        field_ids = list(mock_fields.keys())
        if field_ids:
            # Take first 2-3 fields as updated (or all if fewer than 3)
            num_updated = min(len(field_ids), 3)
            updated_field_ids = field_ids[:num_updated]
            updated_fields = {field_id: mock_fields[field_id] for field_id in updated_field_ids}
        url = f"https://spacenote.app/s/{space.slug}/notes/9999"
    else:
        url = f"https://spacenote.app/s/{space.slug}/notes/9999"

    return NotificationContext(note=note, user=user, space=space, url=url, comment=comment, updated_fields=updated_fields)
