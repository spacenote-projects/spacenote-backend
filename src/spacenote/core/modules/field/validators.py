"""Field validation using validator pattern."""

from spacenote.core.modules.field.models import FieldValueType, SpaceField
from spacenote.core.modules.field.validator_types import create_validator
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User
from spacenote.errors import ValidationError


def parse_field_value(field: SpaceField, raw_value: str, space: Space, members: list[User]) -> FieldValueType:
    """Parse a raw string value based on field type.

    Args:
        field: The field definition from the space
        raw_value: The raw string value to parse
        space: The space this validation is for
        members: List of User objects who are members of the space

    Returns:
        The parsed value in the correct type

    Raises:
        ValidationError: If the value cannot be parsed or validated
    """
    validator = create_validator(field.type, space, members)
    return validator.parse_value(field, raw_value)


def validate_space_field(field: SpaceField, space: Space, members: list[User]) -> SpaceField:
    """Validate field definition.

    Args:
        field: The field definition to validate
        space: The space this validation is for
        members: List of User objects who are members of the space

    Returns:
        A validated SpaceField.
    """
    validator = create_validator(field.type, space, members)
    return validator.validate_definition(field)


def parse_raw_fields(
    space_fields: list[SpaceField], raw_fields: dict[str, str], space: Space, members: list[User]
) -> dict[str, FieldValueType]:
    """Parse raw string fields into typed values based on space field definitions.

    Args:
        space_fields: List of field definitions from the space
        raw_fields: Raw string values from the client
        space: The space this validation is for
        members: List of User objects who are members of the space

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
        parsed_value = parse_field_value(field, raw_value, space, members)

        # Only add non-null values
        if parsed_value is not None:
            parsed_fields[field_name] = parsed_value

    # Add default values for missing optional fields
    for field in space_fields:
        if field.name not in parsed_fields and field.default is not None:
            parsed_fields[field.name] = field.default

    return parsed_fields
