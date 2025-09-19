"""Filter validation utilities."""

from datetime import datetime
from typing import Any
from uuid import UUID

from spacenote.core.modules.field.models import FieldType, FieldValueType, SpaceField
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.errors import ValidationError


def validate_filter_value(field: SpaceField, operator: FilterOperator, value: FieldValueType) -> None:
    """Validate that a filter value is compatible with the field type and operator.

    Args:
        field: The field definition
        operator: The filter operator
        value: The value to validate

    Raises:
        ValidationError: If the value is invalid for the field type or operator
    """
    # For null/None values, only EQ and NE operators are valid
    if value is None:
        if operator not in (FilterOperator.EQ, FilterOperator.NE):
            raise ValidationError(f"Operator '{operator}' cannot be used with null values")
        return

    # Type-specific validation
    if field.type in (FieldType.STRING, FieldType.MARKDOWN):
        _validate_string_value(field, operator, value)
    elif field.type == FieldType.BOOLEAN:
        _validate_boolean_value(field, operator, value)
    elif field.type == FieldType.INT:
        _validate_int_value(field, operator, value)
    elif field.type == FieldType.FLOAT:
        _validate_float_value(field, operator, value)
    elif field.type == FieldType.DATETIME:
        _validate_datetime_value(field, operator, value)
    elif field.type == FieldType.USER:
        _validate_user_value(field, operator, value)
    elif field.type == FieldType.STRING_CHOICE:
        _validate_string_choice_value(field, operator, value)
    elif field.type == FieldType.TAGS:
        _validate_tags_value(field, operator, value)


def _validate_string_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate string field filter value."""
    if not isinstance(value, str):
        raise ValidationError(f"Filter value for string field '{field.name}' must be a string, got {type(value).__name__}")


def _validate_boolean_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate boolean field filter value."""
    if not isinstance(value, bool):
        raise ValidationError(f"Filter value for boolean field '{field.name}' must be a boolean, got {type(value).__name__}")


def _validate_int_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate integer field filter value."""
    if not isinstance(value, int) or isinstance(value, bool):  # bool is subclass of int in Python
        raise ValidationError(f"Filter value for integer field '{field.name}' must be an integer, got {type(value).__name__}")


def _validate_float_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate float field filter value."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValidationError(f"Filter value for float field '{field.name}' must be a number, got {type(value).__name__}")


def _validate_datetime_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate datetime field filter value."""
    if isinstance(value, str):
        # Try to parse as datetime
        try:
            for fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
            ]:
                try:
                    datetime.strptime(value, fmt)  # noqa: DTZ007
                except ValueError:
                    continue
                else:
                    return
            raise ValidationError(f"Invalid datetime format for filter on field '{field.name}': {value}")  # noqa: TRY301
        except Exception as e:
            raise ValidationError(f"Invalid datetime value for filter on field '{field.name}': {value}") from e
    elif not isinstance(value, datetime):
        raise ValidationError(f"Filter value for datetime field '{field.name}' must be a datetime or valid datetime string")


def _validate_user_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate user field filter value."""
    if isinstance(value, str):
        # Accept any string - could be UUID or username
        # Actual validation will happen at query time
        pass
    elif isinstance(value, UUID):
        pass  # Valid UUID
    else:
        raise ValidationError(f"Filter value for user field '{field.name}' must be a UUID or username string")


def _validate_string_choice_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ANN401
    """Validate string choice field filter value."""
    if operator in (FilterOperator.IN, FilterOperator.NIN):
        if not isinstance(value, list):
            raise ValidationError(f"Filter value for operator '{operator}' on field '{field.name}' must be a list")
        for item in value:
            if not isinstance(item, str):
                raise ValidationError(f"All values in list for field '{field.name}' must be strings")
    elif not isinstance(value, str):
        raise ValidationError(f"Filter value for string choice field '{field.name}' must be a string")


def _validate_tags_value(field: SpaceField, operator: FilterOperator, value: Any) -> None:  # noqa: ARG001, ANN401
    """Validate tags field filter value."""
    if not isinstance(value, list):
        raise ValidationError(f"Filter value for tags field '{field.name}' must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValidationError(f"All values in list for tags field '{field.name}' must be strings")
