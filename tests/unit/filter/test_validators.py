"""Tests for filter validators."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from spacenote.core.modules.field.models import FieldType, SpaceField
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.core.modules.filter.validators import (
    validate_boolean_value,
    validate_datetime_value,
    validate_filter_value,
    validate_float_value,
    validate_int_value,
    validate_string_choice_value,
    validate_string_value,
    validate_tags_value,
    validate_user_value,
)
from spacenote.errors import ValidationError


class TestValidateStringValue:
    """Tests for string value validation."""

    def test_valid_string_accepted(self):
        """Test that valid string values are accepted."""
        field = SpaceField(id="title", type=FieldType.STRING, required=True)
        validate_string_value(field, "hello world")

    def test_non_string_raises_error(self):
        """Test that non-string values raise ValidationError."""
        field = SpaceField(id="title", type=FieldType.STRING, required=True)
        with pytest.raises(ValidationError, match="must be a string"):
            validate_string_value(field, 123)


class TestValidateBooleanValue:
    """Tests for boolean value validation."""

    def test_valid_boolean_accepted(self):
        """Test that boolean values are accepted."""
        field = SpaceField(id="active", type=FieldType.BOOLEAN, required=True)
        validate_boolean_value(field, True)
        validate_boolean_value(field, False)

    def test_non_boolean_raises_error(self):
        """Test that non-boolean values raise ValidationError."""
        field = SpaceField(id="active", type=FieldType.BOOLEAN, required=True)
        with pytest.raises(ValidationError, match="must be a boolean"):
            validate_boolean_value(field, "true")


class TestValidateIntValue:
    """Tests for integer value validation."""

    def test_valid_int_accepted(self):
        """Test that integer values are accepted."""
        field = SpaceField(id="count", type=FieldType.INT, required=True)
        validate_int_value(field, 42)
        validate_int_value(field, -10)
        validate_int_value(field, 0)

    def test_float_raises_error(self):
        """Test that float values raise ValidationError."""
        field = SpaceField(id="count", type=FieldType.INT, required=True)
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_int_value(field, 3.14)

    def test_boolean_raises_error(self):
        """Test that boolean values raise ValidationError (bool is subclass of int)."""
        field = SpaceField(id="count", type=FieldType.INT, required=True)
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_int_value(field, True)


class TestValidateFloatValue:
    """Tests for float value validation."""

    def test_valid_float_accepted(self):
        """Test that float values are accepted."""
        field = SpaceField(id="price", type=FieldType.FLOAT, required=True)
        validate_float_value(field, 3.14)
        validate_float_value(field, -2.5)

    def test_int_accepted_for_float(self):
        """Test that integers are accepted for float fields."""
        field = SpaceField(id="price", type=FieldType.FLOAT, required=True)
        validate_float_value(field, 42)

    def test_boolean_raises_error(self):
        """Test that boolean values raise ValidationError."""
        field = SpaceField(id="price", type=FieldType.FLOAT, required=True)
        with pytest.raises(ValidationError, match="must be a number"):
            validate_float_value(field, True)


class TestValidateDatetimeValue:
    """Tests for datetime value validation."""

    def test_datetime_object_accepted(self):
        """Test that datetime objects are accepted."""
        field = SpaceField(id="due_date", type=FieldType.DATETIME, required=True)
        validate_datetime_value(field, datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC))

    def test_valid_iso_string_accepted(self):
        """Test that valid ISO format strings are accepted."""
        field = SpaceField(id="due_date", type=FieldType.DATETIME, required=True)
        validate_datetime_value(field, "2025-01-01T12:00:00")
        validate_datetime_value(field, "2025-01-01")
        validate_datetime_value(field, "2025-01-01T12:00:00Z")

    def test_invalid_string_raises_error(self):
        """Test that invalid datetime strings raise ValidationError."""
        field = SpaceField(id="due_date", type=FieldType.DATETIME, required=True)
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            validate_datetime_value(field, "not-a-date")

    def test_non_datetime_type_raises_error(self):
        """Test that non-datetime types raise ValidationError."""
        field = SpaceField(id="due_date", type=FieldType.DATETIME, required=True)
        with pytest.raises(ValidationError, match="must be a datetime"):
            validate_datetime_value(field, 12345)


class TestValidateUserValue:
    """Tests for user value validation."""

    def test_uuid_accepted(self):
        """Test that UUID values are accepted."""
        field = SpaceField(id="owner", type=FieldType.USER, required=True)
        validate_user_value(field, UUID("12345678-1234-5678-1234-567812345678"))

    def test_string_accepted(self):
        """Test that string values are accepted (username or UUID string)."""
        field = SpaceField(id="owner", type=FieldType.USER, required=True)
        validate_user_value(field, "username")
        validate_user_value(field, "12345678-1234-5678-1234-567812345678")

    def test_non_string_non_uuid_raises_error(self):
        """Test that non-string, non-UUID values raise ValidationError."""
        field = SpaceField(id="owner", type=FieldType.USER, required=True)
        with pytest.raises(ValidationError, match="must be a UUID or username string"):
            validate_user_value(field, 123)


class TestValidateStringChoiceValue:
    """Tests for string choice value validation."""

    def test_single_string_value_accepted(self):
        """Test that single string values are accepted for EQ/NE operators."""
        field = SpaceField(id="status", type=FieldType.STRING_CHOICE, required=True)
        validate_string_choice_value(field, FilterOperator.EQ, "active")

    def test_list_value_for_in_operator(self):
        """Test that list values are accepted for IN operator."""
        field = SpaceField(id="status", type=FieldType.STRING_CHOICE, required=True)
        validate_string_choice_value(field, FilterOperator.IN, ["active", "pending"])

    def test_list_value_for_nin_operator(self):
        """Test that list values are accepted for NIN operator."""
        field = SpaceField(id="status", type=FieldType.STRING_CHOICE, required=True)
        validate_string_choice_value(field, FilterOperator.NIN, ["archived", "deleted"])

    def test_non_list_for_in_raises_error(self):
        """Test that non-list values for IN operator raise ValidationError."""
        field = SpaceField(id="status", type=FieldType.STRING_CHOICE, required=True)
        with pytest.raises(ValidationError, match="must be a list"):
            validate_string_choice_value(field, FilterOperator.IN, "active")

    def test_non_string_in_list_raises_error(self):
        """Test that non-string items in list raise ValidationError."""
        field = SpaceField(id="status", type=FieldType.STRING_CHOICE, required=True)
        with pytest.raises(ValidationError, match="must be strings"):
            validate_string_choice_value(field, FilterOperator.IN, ["active", 123])


class TestValidateTagsValue:
    """Tests for tags value validation."""

    def test_valid_string_list_accepted(self):
        """Test that list of strings is accepted."""
        field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        validate_tags_value(field, ["python", "testing", "refactoring"])

    def test_empty_list_accepted(self):
        """Test that empty list is accepted."""
        field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        validate_tags_value(field, [])

    def test_non_list_raises_error(self):
        """Test that non-list values raise ValidationError."""
        field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        with pytest.raises(ValidationError, match="must be a list"):
            validate_tags_value(field, "python")

    def test_non_string_items_raise_error(self):
        """Test that non-string items in list raise ValidationError."""
        field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        with pytest.raises(ValidationError, match="must be strings"):
            validate_tags_value(field, ["python", 123])


class TestValidateFilterValue:
    """Tests for the main validate_filter_value function."""

    def test_null_value_with_eq_accepted(self):
        """Test that null values are accepted with EQ operator."""
        field = SpaceField(id="title", type=FieldType.STRING, required=False)
        validate_filter_value(field, FilterOperator.EQ, None)

    def test_null_value_with_ne_accepted(self):
        """Test that null values are accepted with NE operator."""
        field = SpaceField(id="title", type=FieldType.STRING, required=False)
        validate_filter_value(field, FilterOperator.NE, None)

    def test_null_value_with_other_operators_raises_error(self):
        """Test that null values with non-equality operators raise ValidationError."""
        field = SpaceField(id="count", type=FieldType.INT, required=False)
        with pytest.raises(ValidationError, match="cannot be used with null values"):
            validate_filter_value(field, FilterOperator.GT, None)

    def test_delegates_to_type_specific_validator(self):
        """Test that validation is delegated to type-specific validators."""
        string_field = SpaceField(id="title", type=FieldType.STRING, required=True)
        validate_filter_value(string_field, FilterOperator.EQ, "test")

        int_field = SpaceField(id="count", type=FieldType.INT, required=True)
        validate_filter_value(int_field, FilterOperator.GT, 5)

    def test_string_choice_validator_receives_operator(self):
        """Test that STRING_CHOICE validator gets operator parameter."""
        field = SpaceField(id="status", type=FieldType.STRING_CHOICE, required=True)
        validate_filter_value(field, FilterOperator.IN, ["active", "pending"])
