"""Image generation and path utilities for IMAGE field type."""

from pathlib import Path

from PIL import Image


def generate_image(source: Path, destination: Path, max_width: int) -> tuple[int, int]:
    """Resize image to max_width while maintaining aspect ratio, save as WebP.

    Args:
        source: Path to the original image file
        destination: Path where the image should be saved
        max_width: Maximum width for the image

    Returns:
        Tuple of (width, height) of the generated image

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


def get_image_path(images_base_path: str, space_slug: str, note_number: int, field_id: str) -> Path:
    """Calculate the storage path for an IMAGE field.

    Args:
        images_base_path: Base directory for all images
        space_slug: Space slug
        note_number: Note number within the space
        field_id: Field identifier

    Returns:
        Full path where the image should be stored
    """
    return Path(images_base_path) / space_slug / str(note_number) / field_id


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
