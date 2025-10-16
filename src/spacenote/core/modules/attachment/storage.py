"""File storage operations for attachments."""

from pathlib import Path

SPACE_ATTACHMENTS_DIR = "__space__"


def write_attachment_file(
    attachments_path: str, space_slug: str, attachment_number: int, note_number: int | None, content: bytes
) -> Path:
    """Write attachment file to disk.

    Args:
        attachments_path: Base path for attachments storage
        space_slug: Space slug
        attachment_number: Attachment number
        note_number: Note number (None for space-level attachments)
        content: File content bytes

    Returns:
        Absolute path to written file
    """
    file_path = get_attachment_file_path(attachments_path, space_slug, attachment_number, note_number)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    return file_path


def move_attachment_file(
    attachments_path: str, space_slug: str, attachment_number: int, old_note_number: int | None, new_note_number: int | None
) -> tuple[Path, Path]:
    """Move attachment file from one location to another.

    Args:
        attachments_path: Base path for attachments storage
        space_slug: Space slug
        attachment_number: Attachment number
        old_note_number: Current note number (None for space-level)
        new_note_number: Target note number (None for space-level)

    Returns:
        Tuple of (old_path, new_path)

    Raises:
        FileNotFoundError: If source file doesn't exist
    """
    old_path = get_attachment_file_path(attachments_path, space_slug, attachment_number, old_note_number)
    new_path = get_attachment_file_path(attachments_path, space_slug, attachment_number, new_note_number)

    if not old_path.exists():
        raise FileNotFoundError(f"Attachment file not found: {old_path}")

    new_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.rename(new_path)
    return old_path, new_path


def get_attachment_file_path(attachments_path: str, space_slug: str, attachment_number: int, note_number: int | None) -> Path:
    """Get absolute path to attachment file.

    Args:
        attachments_path: Base path for attachments storage
        space_slug: Space slug
        attachment_number: Attachment number
        note_number: Note number (None for space-level attachments)

    Returns:
        Absolute path to attachment file
    """
    if note_number is not None:
        return Path(attachments_path) / space_slug / str(note_number) / str(attachment_number)
    return Path(attachments_path) / space_slug / SPACE_ATTACHMENTS_DIR / str(attachment_number)
