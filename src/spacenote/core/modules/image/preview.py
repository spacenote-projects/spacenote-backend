"""Image preview generation and path utilities."""

from pathlib import Path

from PIL import Image


def generate_preview(source: Path, destination: Path, max_width: int) -> tuple[int, int]:
    """Resize image to max_width while maintaining aspect ratio, save as WebP.

    Args:
        source: Path to the original image file
        destination: Path where the preview should be saved
        max_width: Maximum width for the preview image

    Returns:
        Tuple of (width, height) of the generated preview

    Raises:
        OSError: If image cannot be opened or saved
    """
    with Image.open(source) as img:
        original_width, original_height = img.size

        if original_width <= max_width:
            new_width = original_width
            new_height = original_height
        else:
            new_width = max_width
            new_height = int((max_width / original_width) * original_height)

        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        output_dir = destination.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        resized.save(destination, format="WEBP", quality=85)

        return new_width, new_height


def get_preview_path(
    previews_base_path: str, space_slug: str, note_number: int, attachment_number: int, field_id: str, preview_key: str
) -> Path:
    """Calculate the storage path for an image preview.

    Args:
        previews_base_path: Base directory for all previews
        space_slug: Space slug
        note_number: Note number within the space
        attachment_number: Attachment number
        field_id: Field identifier
        preview_key: Preview configuration key (e.g., "thumbnail", "medium")

    Returns:
        Full path where the preview should be stored
    """
    return Path(previews_base_path) / space_slug / str(note_number) / f"{attachment_number}__{field_id}__{preview_key}"


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
