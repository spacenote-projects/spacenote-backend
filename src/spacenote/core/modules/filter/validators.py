"""Filter validation utilities."""

from datetime import datetime
from uuid import UUID

from spacenote.core.modules.field.models import FieldType, FieldValueType, SpaceField
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.errors import ValidationError


def validate_string_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate string field filter value."""
    if not isinstance(value, str):
        raise ValidationError(f"Filter value for string field '{field.id}' must be a string, got {type(value).__name__}")


def validate_boolean_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate boolean field filter value."""
    if not isinstance(value, bool):
        raise ValidationError(f"Filter value for boolean field '{field.id}' must be a boolean, got {type(value).__name__}")


def validate_int_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate integer field filter value."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"Filter value for integer field '{field.id}' must be an integer, got {type(value).__name__}")


def validate_float_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate float field filter value."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValidationError(f"Filter value for float field '{field.id}' must be a number, got {type(value).__name__}")


def validate_datetime_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate datetime field filter value."""
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
                datetime.strptime(value, fmt)  # noqa: DTZ007
            except ValueError:
                continue
            else:
                return
        raise ValidationError(f"Invalid datetime format for filter on field '{field.id}': {value}")

    if not isinstance(value, datetime):
        raise ValidationError(f"Filter value for datetime field '{field.id}' must be a datetime or valid datetime string")


def validate_user_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate user field filter value."""
    if not isinstance(value, str | UUID):
        raise ValidationError(f"Filter value for user field '{field.id}' must be a UUID or username string")


def validate_string_choice_value(field: SpaceField, operator: FilterOperator, value: FieldValueType) -> None:
    """Validate string choice field filter value."""
    if operator in (FilterOperator.IN, FilterOperator.NIN):
        if not isinstance(value, list):
            raise ValidationError(f"Filter value for operator '{operator}' on field '{field.id}' must be a list")
        for item in value:
            if not isinstance(item, str):
                raise ValidationError(f"All values in list for field '{field.id}' must be strings")
    elif not isinstance(value, str):
        raise ValidationError(f"Filter value for string choice field '{field.id}' must be a string")


def validate_tags_value(field: SpaceField, value: FieldValueType) -> None:
    """Validate tags field filter value."""
    if not isinstance(value, list):
        raise ValidationError(f"Filter value for tags field '{field.id}' must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValidationError(f"All values in list for tags field '{field.id}' must be strings")


def validate_filter_value(field: SpaceField, operator: FilterOperator, value: FieldValueType) -> None:
    """Validate that a filter value is compatible with the field type and operator.

    Args:
        field: The field definition
        operator: The filter operator
        value: The value to validate

    Raises:
        ValidationError: If the value is invalid for the field type or operator
    """
    if value is None:  # Null value allowed only with EQ and NE
        if operator not in (FilterOperator.EQ, FilterOperator.NE):
            raise ValidationError(f"Operator '{operator}' cannot be used with null values")
        return

    if field.type == FieldType.STRING_CHOICE:
        validate_string_choice_value(field, operator, value)
    elif field.type in {FieldType.STRING, FieldType.MARKDOWN}:
        validate_string_value(field, value)
    elif field.type == FieldType.BOOLEAN:
        validate_boolean_value(field, value)
    elif field.type == FieldType.INT:
        validate_int_value(field, value)
    elif field.type == FieldType.FLOAT:
        validate_float_value(field, value)
    elif field.type == FieldType.DATETIME:
        validate_datetime_value(field, value)
    elif field.type == FieldType.USER:
        validate_user_value(field, value)
    elif field.type == FieldType.TAGS:
        validate_tags_value(field, value)
