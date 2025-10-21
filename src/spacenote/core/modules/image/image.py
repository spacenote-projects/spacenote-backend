"""Image generation and path utilities for IMAGE field type."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener  # type: ignore[import-untyped]

from spacenote.errors import ValidationError

register_heif_opener()


@dataclass
class WebpOptions:
    """Options for WebP image conversion."""

    max_width: int | None = None


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


def parse_webp_option(option: str | None) -> WebpOptions:
    """Parse WebP conversion option string.

    Args:
        option: Option string in format "max_width:800" or None

    Returns:
        WebpOptions with parsed values

    Raises:
        ValidationError: If option string is invalid
    """
    if option is None:
        return WebpOptions()

    parts = option.split(":")
    if len(parts) != 2:
        raise ValidationError(f"Invalid option format: '{option}' (expected 'key:value')")

    key, value = parts

    if key == "max_width":
        try:
            max_width = int(value)
            if max_width <= 0:
                raise ValidationError(f"max_width must be positive, got: {max_width}")
            return WebpOptions(max_width=max_width)
        except ValueError:
            raise ValidationError(f"Invalid max_width value: '{value}' (expected integer)") from None
    else:
        raise ValidationError(f"Unknown option: '{key}' (supported: max_width)")


def convert_image_to_webp(source: Path, options: WebpOptions) -> bytes:
    """Convert image to WebP format and return as bytes.

    Args:
        source: Path to the original image file
        options: WebP conversion options (max_width, etc.)

    Returns:
        WebP image data as bytes

    Raises:
        OSError: If image cannot be opened or converted
    """
    with Image.open(source) as img:
        if options.max_width is not None and options.max_width > 0:
            original_width, original_height = img.size

            if original_width > options.max_width:
                new_width = options.max_width
                new_height = int((options.max_width / original_width) * original_height)
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                resized = img
        else:
            resized = img

        buffer = BytesIO()
        resized.save(buffer, format="WEBP", quality=85)
        return buffer.getvalue()
