"""Tests for DATETIME field validator."""

from datetime import UTC, datetime

import pytest

from spacenote.core.modules.field.models import FieldType, SpaceField, SpecialValue
from spacenote.core.modules.field.validators import DateTimeValidator
from spacenote.errors import ValidationError


class TestDateTimeFieldDefinition:
    """Tests for datetime field definition validation."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for all tests in this class."""
        self.validator = DateTimeValidator(mock_space, mock_members)

    def test_basic_datetime_field_definition(self):
        """Test basic datetime field definition without default."""
        field = SpaceField(id="event_time", type=FieldType.DATETIME, required=True)
        result = self.validator.validate_field_definition(field)
        assert result.id == "event_time"
        assert result.type == FieldType.DATETIME
        assert result.required is True
        assert result.default is None

    def test_datetime_field_with_now_default(self):
        """Test datetime field with $now special value as default."""
        field = SpaceField(id="created", type=FieldType.DATETIME, default=SpecialValue.NOW)
        result = self.validator.validate_field_definition(field)
        assert result.default == SpecialValue.NOW


class TestDateTimeFieldParsing:
    """Tests for parsing datetime field values."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator and field for parsing tests."""
        self.validator = DateTimeValidator(mock_space, mock_members)
        self.field = SpaceField(id="event_time", type=FieldType.DATETIME, required=True)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_parse_iso_format(self):
        """Test parsing ISO 8601 datetime format."""
        result = self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 20
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_iso_format_with_z_suffix(self):
        """Test parsing ISO format with Z suffix."""
        result = self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 20

    def test_parse_iso_format_with_microseconds(self):
        """Test parsing ISO format with microseconds."""
        result = self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00.123456")
        assert isinstance(result, datetime)
        assert result.microsecond == 123456

    def test_parse_space_separated_format(self):
        """Test parsing space-separated datetime format."""
        result = self.validator.parse_value(self.validated_field, "2025-10-20 14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 20

    def test_parse_date_only(self):
        """Test parsing date-only format (time defaults to 00:00:00)."""
        result = self.validator.parse_value(self.validated_field, "2025-10-20")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 20
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_parse_now_special_value(self):
        """Test parsing $now special value."""
        before = datetime.now(UTC)
        result = self.validator.parse_value(self.validated_field, SpecialValue.NOW)
        after = datetime.now(UTC)

        assert isinstance(result, datetime)
        assert before <= result <= after
        assert result.tzinfo == UTC

    def test_parse_none_required_field_raises_error(self):
        """Test that None value for required field raises error."""
        with pytest.raises(ValidationError, match="Required field"):
            self.validator.parse_value(self.validated_field, None)

    def test_parse_empty_string_required_field_raises_error(self):
        """Test that empty string for required field raises error."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "")

    def test_parse_none_optional_field(self):
        """Test that None value for optional field returns None."""
        optional_field = SpaceField(id="completed_at", type=FieldType.DATETIME, required=False)
        validated = self.validator.validate_field_definition(optional_field)
        assert self.validator.parse_value(validated, None) is None

    def test_parse_empty_string_optional_field(self):
        """Test that empty string for optional field returns None."""
        optional_field = SpaceField(id="completed_at", type=FieldType.DATETIME, required=False)
        validated = self.validator.validate_field_definition(optional_field)
        assert self.validator.parse_value(validated, "") is None

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid datetime format raises error."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "not-a-date")

    def test_parse_partial_date_raises_error(self):
        """Test that partial date raises error."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "2025-10")


class TestDateTimeFieldNowSpecialValue:
    """Tests for $now special value handling."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for $now tests."""
        self.validator = DateTimeValidator(mock_space, mock_members)

    def test_now_default_with_none_value(self):
        """Test that $now default returns current time for None value."""
        field = SpaceField(id="meal_time", type=FieldType.DATETIME, required=True, default=SpecialValue.NOW)
        validated = self.validator.validate_field_definition(field)

        before = datetime.now(UTC)
        result = self.validator.parse_value(validated, None)
        after = datetime.now(UTC)

        assert isinstance(result, datetime)
        assert before <= result <= after
        assert result.tzinfo == UTC

    def test_now_default_can_be_overridden(self):
        """Test that $now default can be overridden with explicit timestamp."""
        field = SpaceField(id="meal_time", type=FieldType.DATETIME, default=SpecialValue.NOW)
        validated = self.validator.validate_field_definition(field)

        result = self.validator.parse_value(validated, "2025-10-18T19:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 18
        assert result.hour == 19
        assert result.minute == 30

    def test_now_explicit_value(self):
        """Test parsing explicit $now value without default."""
        field = SpaceField(id="event_time", type=FieldType.DATETIME)
        validated = self.validator.validate_field_definition(field)

        before = datetime.now(UTC)
        result = self.validator.parse_value(validated, SpecialValue.NOW)
        after = datetime.now(UTC)

        assert isinstance(result, datetime)
        assert before <= result <= after
        assert result.tzinfo == UTC

    def test_required_field_with_now_default_and_empty_value(self):
        """Test required field with $now default handles empty value correctly."""
        field = SpaceField(id="meal_time", type=FieldType.DATETIME, required=True, default=SpecialValue.NOW)
        validated = self.validator.validate_field_definition(field)

        # Empty string for required field should raise error (consistent with other validators)
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(validated, "")


class TestDateTimeFieldEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for edge case tests."""
        self.validator = DateTimeValidator(mock_space, mock_members)

    def test_leap_year_date(self):
        """Test parsing leap year date."""
        field = SpaceField(id="event_time", type=FieldType.DATETIME)
        validated = self.validator.validate_field_definition(field)

        result = self.validator.parse_value(validated, "2024-02-29")
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29

    def test_end_of_year_datetime(self):
        """Test parsing end of year datetime."""
        field = SpaceField(id="event_time", type=FieldType.DATETIME)
        validated = self.validator.validate_field_definition(field)

        result = self.validator.parse_value(validated, "2025-12-31T23:59:59")
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_midnight_time(self):
        """Test parsing midnight time."""
        field = SpaceField(id="event_time", type=FieldType.DATETIME)
        validated = self.validator.validate_field_definition(field)

        result = self.validator.parse_value(validated, "2025-10-20T00:00:00")
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0


class TestDateTimeTimezoneRestrictions:
    """Tests to verify that timezone offsets are not supported."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for timezone restriction tests."""
        self.validator = DateTimeValidator(mock_space, mock_members)
        self.field = SpaceField(id="event_time", type=FieldType.DATETIME, required=True)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_positive_timezone_offset_rejected(self):
        """Test that positive timezone offsets (+03:00) are rejected."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00+03:00")

    def test_negative_timezone_offset_rejected(self):
        """Test that negative timezone offsets (-05:00) are rejected."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00-05:00")

    def test_utc_offset_notation_rejected(self):
        """Test that +00:00 UTC notation is rejected (must use Z or no suffix)."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00+00:00")

    def test_short_timezone_offset_rejected(self):
        """Test that short timezone offsets (+03) are rejected."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.validator.parse_value(self.validated_field, "2025-10-20T14:30:00+03")
