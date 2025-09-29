"""Mock data generator for testing Telegram notifications."""

from typing import Any
from uuid import uuid4

from spacenote.core.modules.field.models import FieldOption, FieldType, FieldValueType
from spacenote.core.modules.space.models import Space
from spacenote.utils import now


def generate_mock_note_fields(space: Space) -> dict[str, FieldValueType]:
    """Generate mock field values based on space field definitions.

    Args:
        space: Space with field definitions

    Returns:
        Dictionary of field_id -> mock value mappings
    """
    mock_fields: dict[str, FieldValueType] = {}

    for field in space.fields:
        if field.type == FieldType.STRING:
            mock_fields[field.id] = f"Test {field.id}"
        elif field.type == FieldType.MARKDOWN:
            mock_fields[field.id] = f"# Test {field.id}\n\nSample markdown content"
        elif field.type == FieldType.BOOLEAN:
            mock_fields[field.id] = True
        elif field.type == FieldType.STRING_CHOICE:
            # Get values from field options
            values = field.options.get(FieldOption.VALUES, [])
            if values and isinstance(values, list):
                mock_fields[field.id] = values[0]
        elif field.type == FieldType.TAGS:
            mock_fields[field.id] = ["tag1", "tag2"]
        elif field.type == FieldType.USER:
            # Generate a mock user UUID
            mock_fields[field.id] = str(uuid4())
        elif field.type == FieldType.DATETIME:
            mock_fields[field.id] = now().isoformat()
        elif field.type == FieldType.INT:
            mock_fields[field.id] = 42
        elif field.type == FieldType.FLOAT:
            mock_fields[field.id] = 3.14

    return mock_fields


def generate_note_created_context(space: Space) -> dict[str, Any]:
    """Generate context for NOTE_CREATED event testing.

    Args:
        space: Space configuration

    Returns:
        Template context with mock note data
    """
    mock_fields = generate_mock_note_fields(space)
    test_time = now()

    return {
        "note": {
            "number": 9999,
            "fields": mock_fields,
            "created_at": test_time.isoformat(),
            "edited_at": None,
            "activity_at": test_time.isoformat(),
        },
        "user": {
            "username": "test_user",
        },
        "space": {
            "title": space.title,
            "slug": space.slug,
        },
        "url": f"https://spacenote.app/spaces/{space.slug}/notes/9999",
    }


def generate_note_updated_context(space: Space) -> dict[str, Any]:
    """Generate context for NOTE_UPDATED event testing.

    Args:
        space: Space configuration

    Returns:
        Template context with mock updated note data
    """
    mock_fields = generate_mock_note_fields(space)
    created_time = now()
    edited_time = now()

    return {
        "note": {
            "number": 9999,
            "fields": mock_fields,
            "created_at": created_time.isoformat(),
            "edited_at": edited_time.isoformat(),
            "activity_at": edited_time.isoformat(),
        },
        "user": {
            "username": "test_user",
        },
        "space": {
            "title": space.title,
            "slug": space.slug,
        },
        "url": f"https://spacenote.app/spaces/{space.slug}/notes/9999",
    }


def generate_comment_created_context(space: Space) -> dict[str, Any]:
    """Generate context for COMMENT_CREATED event testing.

    Args:
        space: Space configuration

    Returns:
        Template context with mock comment data
    """
    mock_fields = generate_mock_note_fields(space)
    test_time = now()

    return {
        "note": {
            "number": 9999,
            "fields": mock_fields,
        },
        "comment": {
            "content": "This is a test comment for notification testing. "
            "It demonstrates how your comment notifications will appear.",
            "number": 1,
            "created_at": test_time.isoformat(),
        },
        "user": {
            "username": "test_user",
        },
        "space": {
            "title": space.title,
            "slug": space.slug,
        },
        "url": f"https://spacenote.app/spaces/{space.slug}/notes/9999#comment-1",
    }
