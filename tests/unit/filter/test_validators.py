"""Tests for filter validators."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.core.modules.filter.validators import (
    validate_boolean_value,
    validate_datetime_value,
    validate_filter_value,
    validate_float_value,
    validate_int_value,
    validate_select_value,
    validate_string_value,
    validate_tags_value,
    validate_user_value,
)
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User
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
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        result = validate_user_value(field, user_id, space, [user])
        assert result == user_id

    def test_username_converted_to_uuid(self):
        """Test that username strings are converted to UUID."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        result = validate_user_value(field, "testuser", space, [user])
        assert result == user_id

    def test_uuid_string_converted_to_uuid(self):
        """Test that UUID strings are converted to UUID objects."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        result = validate_user_value(field, "12345678-1234-5678-1234-567812345678", space, [user])
        assert result == user_id

    def test_special_value_me_preserved(self):
        """Test that $me special value is preserved."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        result = validate_user_value(field, "$me", space, [user])
        assert result == "$me"

    def test_non_member_uuid_raises_error(self):
        """Test that UUID not in space members raises ValidationError."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        other_id = UUID("87654321-4321-8765-4321-876543218765")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        with pytest.raises(ValidationError, match="not a member of this space"):
            validate_user_value(field, other_id, space, [user])

    def test_non_member_username_raises_error(self):
        """Test that username not in space members raises ValidationError."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        with pytest.raises(ValidationError, match="not found or not a member"):
            validate_user_value(field, "otheruser", space, [user])

    def test_non_string_non_uuid_raises_error(self):
        """Test that non-string, non-UUID values raise ValidationError."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        space = Space(id=uuid4(), slug="test", title="Test", members=[user_id], fields=[])
        user = User(id=user_id, username="testuser", password_hash="hash")
        field = SpaceField(id="owner", type=FieldType.USER, required=True)

        with pytest.raises(ValidationError, match="must be a UUID, username string"):
            validate_user_value(field, 123, space, [user])


class TestValidateSelectValue:
    """Tests for select value validation."""

    def test_single_string_value_accepted(self):
        """Test that single string values are accepted for EQ/NE operators."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending", "archived", "deleted"]},
        )
        validate_select_value(field, FilterOperator.EQ, "active")

    def test_list_value_for_in_operator(self):
        """Test that list values are accepted for IN operator."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending", "archived", "deleted"]},
        )
        validate_select_value(field, FilterOperator.IN, ["active", "pending"])

    def test_list_value_for_nin_operator(self):
        """Test that list values are accepted for NIN operator."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending", "archived", "deleted"]},
        )
        validate_select_value(field, FilterOperator.NIN, ["archived", "deleted"])

    def test_non_list_for_in_raises_error(self):
        """Test that non-list values for IN operator raise ValidationError."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending"]},
        )
        with pytest.raises(ValidationError, match="must be a list"):
            validate_select_value(field, FilterOperator.IN, "active")

    def test_non_string_in_list_raises_error(self):
        """Test that non-string items in list raise ValidationError."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending"]},
        )
        with pytest.raises(ValidationError, match="must be strings"):
            validate_select_value(field, FilterOperator.IN, ["active", 123])

    def test_invalid_single_value_raises_error(self):
        """Test that value not in allowed list raises ValidationError."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending"]},
        )
        with pytest.raises(ValidationError, match=r"Invalid choice.*'invalid'.*Allowed values: active, pending"):
            validate_select_value(field, FilterOperator.EQ, "invalid")

    def test_invalid_value_in_list_raises_error(self):
        """Test that invalid value in list raises ValidationError."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending"]},
        )
        with pytest.raises(ValidationError, match=r"Invalid choice.*'invalid'.*Allowed values: active, pending"):
            validate_select_value(field, FilterOperator.IN, ["active", "invalid"])

    def test_missing_values_option_raises_error(self):
        """Test that missing VALUES option raises ValidationError."""
        field = SpaceField(id="status", type=FieldType.SELECT, required=True)
        with pytest.raises(ValidationError, match="must have VALUES option defined"):
            validate_select_value(field, FilterOperator.EQ, "active")


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
        space = Space(id=uuid4(), slug="test", title="Test", members=[], fields=[])
        field = SpaceField(id="title", type=FieldType.STRING, required=False)
        result = validate_filter_value(field, FilterOperator.EQ, None, space, [])
        assert result is None

    def test_null_value_with_ne_accepted(self):
        """Test that null values are accepted with NE operator."""
        space = Space(id=uuid4(), slug="test", title="Test", members=[], fields=[])
        field = SpaceField(id="title", type=FieldType.STRING, required=False)
        result = validate_filter_value(field, FilterOperator.NE, None, space, [])
        assert result is None

    def test_null_value_with_other_operators_raises_error(self):
        """Test that null values with non-equality operators raise ValidationError."""
        space = Space(id=uuid4(), slug="test", title="Test", members=[], fields=[])
        field = SpaceField(id="count", type=FieldType.INT, required=False)
        with pytest.raises(ValidationError, match="cannot be used with null values"):
            validate_filter_value(field, FilterOperator.GT, None, space, [])

    def test_delegates_to_type_specific_validator(self):
        """Test that validation is delegated to type-specific validators."""
        space = Space(id=uuid4(), slug="test", title="Test", members=[], fields=[])
        string_field = SpaceField(id="title", type=FieldType.STRING, required=True)
        result = validate_filter_value(string_field, FilterOperator.EQ, "test", space, [])
        assert result == "test"

        int_field = SpaceField(id="count", type=FieldType.INT, required=True)
        result = validate_filter_value(int_field, FilterOperator.GT, 5, space, [])
        assert result == 5

    def test_select_validator_receives_operator(self):
        """Test that SELECT validator gets operator parameter."""
        space = Space(id=uuid4(), slug="test", title="Test", members=[], fields=[])
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={FieldOption.VALUES: ["active", "pending"]},
        )
        result = validate_filter_value(field, FilterOperator.IN, ["active", "pending"], space, [])
        assert result == ["active", "pending"]
