"""Filter validation utilities."""

from datetime import datetime
from uuid import UUID

from spacenote.core.modules.field.models import FieldOption, FieldType, FieldValueType, SpaceField, SpecialValue
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User
from spacenote.errors import ValidationError


def validate_string_value(field: SpaceField, value: FieldValueType) -> str:
    """Validate and normalize string field filter value."""
    if not isinstance(value, str):
        raise ValidationError(f"Filter value for string field '{field.id}' must be a string, got {type(value).__name__}")
    return value


def validate_boolean_value(field: SpaceField, value: FieldValueType) -> bool:
    """Validate and normalize boolean field filter value."""
    if not isinstance(value, bool):
        raise ValidationError(f"Filter value for boolean field '{field.id}' must be a boolean, got {type(value).__name__}")
    return value


def validate_int_value(field: SpaceField, value: FieldValueType) -> int:
    """Validate and normalize integer field filter value."""
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as e:
            raise ValidationError(f"Filter value for integer field '{field.id}' must be an integer, got string: {value}") from e

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"Filter value for integer field '{field.id}' must be an integer, got {type(value).__name__}")

    return value


def validate_float_value(field: SpaceField, value: FieldValueType) -> float:
    """Validate and normalize float field filter value."""
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as e:
            raise ValidationError(f"Filter value for float field '{field.id}' must be a number, got string: {value}") from e

    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValidationError(f"Filter value for float field '{field.id}' must be a number, got {type(value).__name__}")

    return float(value)


def validate_datetime_value(field: SpaceField, value: FieldValueType) -> datetime:
    """Validate and normalize datetime field filter value."""
    if isinstance(value, str):
        datetime_formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        for fmt in datetime_formats:
            try:
                return datetime.strptime(value, fmt)  # noqa: DTZ007
            except ValueError:
                continue
        raise ValidationError(f"Invalid datetime format for filter on field '{field.id}': {value}")

    if not isinstance(value, datetime):
        raise ValidationError(f"Filter value for datetime field '{field.id}' must be a datetime or valid datetime string")

    return value


def validate_user_value(field: SpaceField, value: FieldValueType, space: Space, members: list[User]) -> UUID | str:
    """Validate and normalize user field filter value."""
    # Keep special value $me as-is
    if value == SpecialValue.ME:
        return SpecialValue.ME

    # UUID value (already normalized by Pydantic)
    if isinstance(value, UUID):
        # Verify user is a member
        if value not in space.members:
            raise ValidationError(f"User with ID '{value}' is not a member of this space")
        return value

    # String value - could be username or UUID string
    if isinstance(value, str):
        # Try to parse as UUID first
        try:
            user_id = UUID(value)
            if user_id not in space.members:
                raise ValidationError(f"User with ID '{user_id}' is not a member of this space")
        except ValueError:
            # Not a UUID, try as username
            user = next((u for u in members if u.username == value), None)
            if not user:
                raise ValidationError(f"User '{value}' not found or not a member of this space") from None
            return user.id
        else:
            return user_id

    raise ValidationError(f"Filter value for user field '{field.id}' must be a UUID, username string, or '$me'")


def validate_select_value(field: SpaceField, operator: FilterOperator, value: FieldValueType) -> str | list[str]:
    """Validate and normalize select field filter value."""
    # Get allowed values from field options
    allowed_values = field.options.get(FieldOption.VALUES)
    if not allowed_values or not isinstance(allowed_values, list):
        raise ValidationError(f"Select field '{field.id}' must have VALUES option defined")

    if operator in (FilterOperator.IN, FilterOperator.NIN):
        if not isinstance(value, list):
            raise ValidationError(f"Filter value for operator '{operator}' on field '{field.id}' must be a list")
        for item in value:
            if not isinstance(item, str):
                raise ValidationError(f"All values in list for field '{field.id}' must be strings")
            if item not in allowed_values:
                raise ValidationError(
                    f"Invalid choice for field '{field.id}': '{item}'. Allowed values: {', '.join(allowed_values)}"
                )
        return value

    if not isinstance(value, str):
        raise ValidationError(f"Filter value for select field '{field.id}' must be a string")
    if value not in allowed_values:
        raise ValidationError(f"Invalid choice for field '{field.id}': '{value}'. Allowed values: {', '.join(allowed_values)}")
    return value


def validate_tags_value(field: SpaceField, value: FieldValueType) -> list[str]:
    """Validate and normalize tags field filter value."""
    if not isinstance(value, list):
        raise ValidationError(f"Filter value for tags field '{field.id}' must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValidationError(f"All values in list for tags field '{field.id}' must be strings")
    return value


def validate_filter_value(
    field: SpaceField, operator: FilterOperator, value: FieldValueType, space: Space, members: list[User]
) -> FieldValueType:
    """Validate and normalize a filter value to match storage format.

    Args:
        field: The field definition
        operator: The filter operator
        value: The value to validate and normalize
        space: The space containing the field
        members: List of space members (for user field validation)

    Returns:
        Normalized value ready for storage

    Raises:
        ValidationError: If the value is invalid for the field type or operator
    """
    if value is None:  # Null value allowed only with EQ and NE
        if operator not in (FilterOperator.EQ, FilterOperator.NE):
            raise ValidationError(f"Operator '{operator}' cannot be used with null values")
        return None

    if field.type == FieldType.SELECT:
        return validate_select_value(field, operator, value)
    if field.type in {FieldType.STRING, FieldType.MARKDOWN}:
        return validate_string_value(field, value)
    if field.type == FieldType.BOOLEAN:
        return validate_boolean_value(field, value)
    if field.type == FieldType.INT:
        return validate_int_value(field, value)
    if field.type == FieldType.FLOAT:
        return validate_float_value(field, value)
    if field.type == FieldType.DATETIME:
        return validate_datetime_value(field, value)
    if field.type == FieldType.USER:
        return validate_user_value(field, value, space, members)
    if field.type == FieldType.TAGS:
        return validate_tags_value(field, value)

    return value
