"""Utility functions for attachment handling."""

import re
from pathlib import Path

SPACE_ATTACHMENTS_DIR = "__space__"


def get_attachment_storage_path(
    space_slug: str,
    attachment_number: int,
    filename: str,
    note_number: int | None = None,
) -> Path:
    """Calculate storage path for an attachment.

    Args:
        space_slug: Space slug
        attachment_number: Attachment number (unique within space)
        filename: Original filename (will be sanitized)
        note_number: Note number if attachment belongs to a note

    Returns:
        Relative path within attachments directory
    """
    sanitized = sanitize_filename(filename)
    file_part = f"{attachment_number}__{sanitized}"

    if note_number is not None:
        return Path(f"{space_slug}/{note_number}/{file_part}")
    return Path(f"{space_slug}/{SPACE_ATTACHMENTS_DIR}/{file_part}")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem storage on Unix-like systems.

    Removes dangerous characters, prevents path traversal, and handles edge cases
    while preserving readability and file extensions.

    Args:
        filename: Original filename from user

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove path components to prevent traversal attacks
    filename = Path(filename).name

    # Remove leading dots to prevent hidden files
    filename = filename.lstrip(".")

    # Replace dangerous characters with underscores
    # Allow only word characters, spaces, dots, and hyphens
    sanitized = re.sub(r"[^\w\s.-]", "_", filename)

    # Replace multiple underscores with single underscore
    sanitized = re.sub(r"_+", "_", sanitized)

    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)

    # Limit length to 100 characters while preserving extension
    if len(sanitized) > 100:
        parts = sanitized.rsplit(".", 1)
        if len(parts) == 2:
            name, ext = parts
            max_name_len = 96 - len(ext)
            sanitized = f"{name[:max_name_len]}.{ext}" if max_name_len > 0 else f"file.{ext}"
        else:
            sanitized = sanitized[:100]

    # Ensure non-empty and meaningful result
    # Check if result is empty or contains only whitespace/underscores/dots/hyphens
    if not sanitized or not re.sub(r"[\s._-]", "", sanitized):
        sanitized = "unnamed_file"

    return sanitized
