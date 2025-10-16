"""Tests for IMAGE field validator."""

from uuid import uuid4

import pytest

from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.core.modules.field.validators import create_validator
from spacenote.core.modules.space.models import Space
from spacenote.errors import ValidationError


class TestImageValidator:
    """Tests for ImageValidator field type."""

    @pytest.fixture
    def space(self):
        """Create a minimal space for testing."""
        return Space(
            slug="test",
            title="Test Space",
            description="",
            owner_id=uuid4(),
            members=[],
            fields=[],
            list_fields=[],
            hidden_create_fields=[],
            comment_editable_fields=[],
        )

    def test_valid_attachment_id(self, space):
        """Test that valid UUID is parsed correctly."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=False,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        attachment_id = uuid4()
        result = validator.parse_value(field, str(attachment_id))
        assert result == attachment_id

    def test_invalid_uuid(self, space):
        """Test that invalid UUID raises error."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=False,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="Invalid UUID"):
            validator.parse_value(field, "not-a-uuid")

    def test_empty_string_returns_none(self, space):
        """Test that empty string returns None for optional field."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=False,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        result = validator.parse_value(field, "")
        assert result is None

    def test_empty_string_required_field_raises(self, space):
        """Test that empty string raises error for required field."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=True,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="Required field"):
            validator.parse_value(field, "")

    def test_none_value_returns_none(self, space):
        """Test that None returns None for optional field."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=False,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        result = validator.parse_value(field, None)
        assert result is None

    def test_none_value_required_field_raises(self, space):
        """Test that None raises error for required field."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=True,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="Required field"):
            validator.parse_value(field, None)

    def test_default_value_when_none(self, space):
        """Test that default value is returned when input is None."""
        default_attachment_id = uuid4()
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=False,
            default=default_attachment_id,
            options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 200}}},
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        result = validator.parse_value(field, None)
        assert result == default_attachment_id

    def test_field_definition_requires_previews(self, space):
        """Test that field definition must have previews option."""
        field = SpaceField(id="photo", type=FieldType.IMAGE, required=False, options={})
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="must have 'previews' option"):
            validator.validate_field_definition(field)

    def test_previews_cannot_be_empty(self, space):
        """Test that previews dictionary cannot be empty."""
        field = SpaceField(id="photo", type=FieldType.IMAGE, required=False, options={FieldOption.PREVIEWS: {}})
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate_field_definition(field)

    def test_preview_config_must_have_max_width(self, space):
        """Test that preview config must have max_width."""
        field = SpaceField(id="photo", type=FieldType.IMAGE, required=False, options={FieldOption.PREVIEWS: {"thumbnail": {}}})
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="must have 'max_width'"):
            validator.validate_field_definition(field)

    def test_max_width_must_be_positive_integer(self, space):
        """Test that max_width must be a positive integer."""
        field = SpaceField(
            id="photo", type=FieldType.IMAGE, required=False, options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": -100}}}
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validator.validate_field_definition(field)

    def test_max_width_zero_is_invalid(self, space):
        """Test that max_width cannot be zero."""
        field = SpaceField(
            id="photo", type=FieldType.IMAGE, required=False, options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": 0}}}
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validator.validate_field_definition(field)

    def test_max_width_string_is_invalid(self, space):
        """Test that max_width must be an integer, not string."""
        field = SpaceField(
            id="photo", type=FieldType.IMAGE, required=False, options={FieldOption.PREVIEWS: {"thumbnail": {"max_width": "200"}}}
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validator.validate_field_definition(field)

    def test_multiple_preview_sizes(self, space):
        """Test that multiple preview sizes can be configured."""
        field = SpaceField(
            id="photo",
            type=FieldType.IMAGE,
            required=False,
            options={
                FieldOption.PREVIEWS: {
                    "thumbnail": {"max_width": 200},
                    "medium": {"max_width": 600},
                    "large": {"max_width": 1200},
                }
            },
        )
        validator = create_validator(FieldType.IMAGE, space, members=[])
        validated_field = validator.validate_field_definition(field)
        assert validated_field == field
