"""EXIF metadata extraction from images."""

from pathlib import Path

from PIL import Image
from PIL.ExifTags import GPSTAGS, IFD, TAGS


def extract_exif(file_path: Path) -> dict[str, str]:
    """Extract EXIF metadata from an image file.

    Args:
        file_path: Path to the image file

    Returns:
        Dictionary mapping EXIF tag names to string values.
        Returns empty dict if image has no EXIF data or cannot be read.
    """
    try:
        with Image.open(file_path) as img:
            exif_data = img.getexif()
            if not exif_data:
                return {}

            result: dict[str, str] = {}

            # Extract base EXIF tags
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id)
                if not tag_name:
                    continue

                if tag_name == "GPSInfo":
                    gps_data = _extract_gps_info(value)
                    result.update(gps_data)
                else:
                    str_value = _convert_value_to_string(value)
                    if str_value is not None:
                        result[tag_name] = str_value

            # Extract extended EXIF tags from Exif sub-IFD
            try:
                exif_ifd = exif_data.get_ifd(IFD.Exif)
                for tag_id, value in exif_ifd.items():
                    tag_name = TAGS.get(tag_id)
                    if not tag_name:
                        continue

                    str_value = _convert_value_to_string(value)
                    if str_value is not None:
                        result[tag_name] = str_value
            except (KeyError, AttributeError):
                pass

            # Extract Interoperability tags
            try:
                interop_ifd = exif_data.get_ifd(IFD.Interop)
                for tag_id, value in interop_ifd.items():
                    tag_name = TAGS.get(tag_id)
                    if not tag_name:
                        continue

                    str_value = _convert_value_to_string(value)
                    if str_value is not None:
                        result[tag_name] = str_value
            except (KeyError, AttributeError):
                pass

            return result
    except Exception:
        return {}


def _extract_gps_info(gps_ifd: dict) -> dict[str, str]:
    """Extract GPS information from GPS IFD.

    Args:
        gps_ifd: GPS IFD dictionary from EXIF

    Returns:
        Dictionary mapping GPS tag names to string values
    """
    result: dict[str, str] = {}

    for tag_id, value in gps_ifd.items():
        tag_name = GPSTAGS.get(tag_id)
        if not tag_name:
            continue

        str_value = _convert_value_to_string(value)
        if str_value is not None:
            result[tag_name] = str_value

    return result


def _convert_value_to_string(value: object) -> str | None:
    """Convert EXIF value to string representation.

    Args:
        value: EXIF value of any type

    Returns:
        String representation or None if conversion fails
    """
    try:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore").rstrip("\x00")
            except Exception:
                return value.hex()
        elif isinstance(value, (tuple, list)):
            return ", ".join(str(v) for v in value)
        else:
            return str(value)
    except Exception:
        return None
