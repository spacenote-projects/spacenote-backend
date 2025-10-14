"""Utility functions for image field handling."""

from pathlib import Path
from uuid import UUID

from PIL import Image


def get_preview_path(
    previews_base_path: str,
    space_id: UUID,
    note_number: int,
    field_id: str,
    attachment_id: UUID,
    preview_key: str,
) -> str:
    """Calculate the storage path for an image preview.

    Args:
        previews_base_path: Base directory for all previews
        space_id: ID of the space
        note_number: Note number within the space
        field_id: Field identifier
        attachment_id: ID of the attachment
        preview_key: Preview configuration key (e.g., "thumbnail", "medium")

    Returns:
        Full path where the preview should be stored
    """
    return f"{previews_base_path}/{space_id}/{note_number}/{field_id}/{attachment_id}/{preview_key}.webp"


def is_valid_image(source: Path) -> bool:
    """Check if a file is a valid image that can be opened by PIL.

    Args:
        source: Path to the file to check

    Returns:
        True if the file is a valid image, False otherwise
    """
    try:
        with Image.open(source) as img:
            img.verify()
    except Exception:
        return False
    else:
        return True
