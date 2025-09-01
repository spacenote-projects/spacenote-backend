from datetime import datetime

from spacenote.core.modules.field.models import FieldOption, FieldType, FieldValueType, SpaceField
from spacenote.errors import ValidationError


def parse_field_value(field: SpaceField, raw_value: str) -> FieldValueType:
    """Parse a raw string value based on field type.

    Args:
        field: The field definition from the space
        raw_value: The raw string value to parse

    Returns:
        The parsed value in the correct type

    Raises:
        ValidationError: If the value cannot be parsed or validated
    """
    # Handle empty strings for optional fields
    if raw_value == "" and not field.required:
        return None

    match field.type:
        case FieldType.STRING | FieldType.MARKDOWN | FieldType.USER:
            return raw_value

        case FieldType.BOOLEAN:
            if raw_value.lower() in ("true", "1", "yes", "on"):
                return True
            if raw_value.lower() in ("false", "0", "no", "off", ""):
                return False
            raise ValidationError(f"Invalid boolean value for field '{field.name}': {raw_value}")

        case FieldType.INT:
            try:
                int_value = int(raw_value)
            except ValueError as e:
                raise ValidationError(f"Invalid integer value for field '{field.name}': {raw_value}") from e
            _validate_numeric_range(field, int_value)
            return int_value

        case FieldType.FLOAT:
            try:
                float_value = float(raw_value)
            except ValueError as e:
                raise ValidationError(f"Invalid float value for field '{field.name}': {raw_value}") from e
            _validate_numeric_range(field, float_value)
            return float_value

        case FieldType.STRING_CHOICE:
            if FieldOption.VALUES in field.options:
                allowed_values = field.options[FieldOption.VALUES]
                if not isinstance(allowed_values, list):
                    raise ValidationError("Invalid field configuration: VALUES must be a list")
                if raw_value not in allowed_values:
                    raise ValidationError(
                        f"Invalid choice for field '{field.name}': '{raw_value}'. Allowed values: {', '.join(allowed_values)}"
                    )
            return raw_value

        case FieldType.TAGS:
            tags = [tag.strip() for tag in raw_value.split(",") if tag.strip()]
            if FieldOption.VALUES in field.options:
                allowed_values = field.options[FieldOption.VALUES]
                if not isinstance(allowed_values, list):
                    raise ValidationError("Invalid field configuration: VALUES must be a list")
                invalid_tags = [tag for tag in tags if tag not in allowed_values]
                if invalid_tags:
                    raise ValidationError(
                        f"Invalid tags for field '{field.name}': {', '.join(invalid_tags)}. "
                        f"Allowed values: {', '.join(allowed_values)}"
                    )
            return tags

        case FieldType.DATETIME:
            # Try common datetime formats
            for fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
            ]:
                try:
                    return datetime.strptime(raw_value, fmt)  # noqa: DTZ007
                except ValueError:
                    continue
            raise ValidationError(f"Invalid datetime format for field '{field.name}': {raw_value}")

        case _:
            raise ValidationError(f"Unknown field type: {field.type}")


def _validate_numeric_range(field: SpaceField, value: float) -> None:
    """Validate numeric value is within min/max range."""
    if FieldOption.MIN in field.options:
        min_val = field.options[FieldOption.MIN]
        if isinstance(min_val, (int, float)) and value < min_val:
            raise ValidationError(f"Value for field '{field.name}' is below minimum: {value} < {min_val}")

    if FieldOption.MAX in field.options:
        max_val = field.options[FieldOption.MAX]
        if isinstance(max_val, (int, float)) and value > max_val:
            raise ValidationError(f"Value for field '{field.name}' is above maximum: {value} > {max_val}")


def parse_raw_fields(space_fields: list[SpaceField], raw_fields: dict[str, str]) -> dict[str, FieldValueType]:
    """Parse raw string fields into typed values based on space field definitions.

    Args:
        space_fields: List of field definitions from the space
        raw_fields: Raw string values from the client

    Returns:
        Dictionary of parsed field values

    Raises:
        ValidationError: If required fields are missing or values are invalid
    """
    parsed_fields: dict[str, FieldValueType] = {}

    # Create a map for quick lookup
    field_map = {field.name: field for field in space_fields}

    # Check for required fields
    for field in space_fields:
        if field.required and field.name not in raw_fields:
            raise ValidationError(f"Required field missing: {field.name}")

    # Parse each provided field
    for field_name, raw_value in raw_fields.items():
        if field_name not in field_map:
            raise ValidationError(f"Unknown field: {field_name}")

        field = field_map[field_name]
        parsed_value = parse_field_value(field, raw_value)

        # Only add non-null values
        if parsed_value is not None:
            parsed_fields[field_name] = parsed_value

    # Add default values for missing optional fields
    for field in space_fields:
        if field.name not in parsed_fields and field.default is not None:
            parsed_fields[field.name] = field.default

    return parsed_fields


def validate_space_field(field: SpaceField) -> SpaceField:
    """Validate field definition.

    Returns a validated SpaceField.
    """
    # Validate field name format
    if not field.name or not field.name.replace("_", "").isalnum():
        raise ValidationError(f"Invalid field name: {field.name}")

    # Type-specific validation
    match field.type:
        case FieldType.STRING_CHOICE:
            if FieldOption.VALUES not in field.options:
                raise ValidationError("String choice fields must have 'values' option")
            values = field.options[FieldOption.VALUES]
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ValidationError("String choice 'values' must be a list of strings")

        case FieldType.INT | FieldType.FLOAT:
            for opt in (FieldOption.MIN, FieldOption.MAX):
                if opt in field.options:
                    val = field.options[opt]
                    if not isinstance(val, (int, float)):
                        raise ValidationError(f"{opt} must be numeric")

        case FieldType.BOOLEAN:
            if field.default is not None and not isinstance(field.default, bool):
                raise ValidationError("Boolean field default must be boolean")

    return field
