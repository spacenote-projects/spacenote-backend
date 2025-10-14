"""Image processing utilities for preview generation."""

from pathlib import Path

from PIL import Image


def generate_preview(image_path: str, output_path: str, max_width: int) -> tuple[int, int]:
    """Resize image to max_width while maintaining aspect ratio, save as WebP.

    Args:
        image_path: Path to the original image file
        output_path: Path where the preview should be saved
        max_width: Maximum width for the preview image

    Returns:
        Tuple of (width, height) of the generated preview

    Raises:
        OSError: If image cannot be opened or saved
    """
    with Image.open(image_path) as img:
        original_width, original_height = img.size

        if original_width <= max_width:
            new_width = original_width
            new_height = original_height
        else:
            new_width = max_width
            new_height = int((max_width / original_width) * original_height)

        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        resized.save(output_path, format="WEBP", quality=85)

        return new_width, new_height
