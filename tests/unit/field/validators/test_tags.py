"""Tests for TAGS field validator."""

import pytest

from spacenote.core.modules.field.models import FieldType, SpaceField
from spacenote.core.modules.field.validators import TagsValidator
from spacenote.errors import ValidationError


class TestTagsFieldDefinition:
    """Tests for tags field definition validation."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for all tests in this class."""
        self.validator = TagsValidator(mock_space, mock_members)

    def test_basic_tags_field_definition(self):
        """Test basic tags field definition."""
        field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        result = self.validator.validate_field_definition(field)
        assert result.id == "tags"
        assert result.type == FieldType.TAGS
        assert result.required is False
        assert result.default is None

    def test_required_tags_field_definition(self):
        """Test required tags field definition."""
        field = SpaceField(id="categories", type=FieldType.TAGS, required=True)
        result = self.validator.validate_field_definition(field)
        assert result.required is True

    def test_tags_field_with_default(self):
        """Test tags field with default value."""
        default_tags = ["python", "backend"]
        field = SpaceField(id="tech_stack", type=FieldType.TAGS, default=default_tags)
        result = self.validator.validate_field_definition(field)
        assert result.default == default_tags


class TestTagsFieldParsing:
    """Tests for parsing tags field values."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator and field for parsing tests."""
        self.validator = TagsValidator(mock_space, mock_members)
        self.field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_parse_single_tag(self):
        """Test parsing a single tag."""
        result = self.validator.parse_value(self.validated_field, "python")
        assert result == ["python"]

    def test_parse_multiple_tags(self):
        """Test parsing multiple comma-separated tags."""
        result = self.validator.parse_value(self.validated_field, "python,javascript,rust")
        assert result == ["python", "javascript", "rust"]

    def test_parse_tags_with_spaces(self):
        """Test that whitespace around tags is trimmed."""
        result = self.validator.parse_value(self.validated_field, "python, javascript , rust")
        assert result == ["python", "javascript", "rust"]

    def test_parse_tags_removes_duplicates(self):
        """Test that duplicate tags are removed while preserving order."""
        result = self.validator.parse_value(self.validated_field, "python,testing,python,refactoring")
        assert result == ["python", "testing", "refactoring"]

    def test_parse_tags_removes_duplicates_with_spaces(self):
        """Test duplicate removal works with whitespace."""
        result = self.validator.parse_value(self.validated_field, "python, testing, python , testing, refactoring")
        assert result == ["python", "testing", "refactoring"]

    def test_parse_tags_preserves_first_occurrence_order(self):
        """Test that first occurrence order is preserved when removing duplicates."""
        result = self.validator.parse_value(self.validated_field, "z,a,z,b,a,c")
        assert result == ["z", "a", "b", "c"]

    def test_parse_empty_string_optional_field(self):
        """Test that empty string returns None for optional field."""
        result = self.validator.parse_value(self.validated_field, "")
        assert result is None

    def test_parse_none_optional_field(self):
        """Test that None value returns None for optional field."""
        result = self.validator.parse_value(self.validated_field, None)
        assert result is None

    def test_parse_tags_with_trailing_commas(self):
        """Test parsing tags with trailing commas."""
        result = self.validator.parse_value(self.validated_field, "python,javascript,")
        assert result == ["python", "javascript"]

    def test_parse_tags_with_leading_commas(self):
        """Test parsing tags with leading commas."""
        result = self.validator.parse_value(self.validated_field, ",python,javascript")
        assert result == ["python", "javascript"]

    def test_parse_tags_with_multiple_consecutive_commas(self):
        """Test parsing tags with multiple consecutive commas."""
        result = self.validator.parse_value(self.validated_field, "python,,,,javascript")
        assert result == ["python", "javascript"]

    def test_parse_only_commas_returns_empty_list(self):
        """Test that string with only commas returns empty list."""
        result = self.validator.parse_value(self.validated_field, ",,,")
        assert result == []

    def test_parse_only_spaces_returns_empty_list(self):
        """Test that string with only spaces returns empty list."""
        result = self.validator.parse_value(self.validated_field, "   ")
        assert result == []


class TestTagsFieldRequired:
    """Tests for required tags field validation."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator and required field for tests."""
        self.validator = TagsValidator(mock_space, mock_members)
        self.field = SpaceField(id="categories", type=FieldType.TAGS, required=True)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_parse_none_required_field_raises_error(self):
        """Test that None value for required field raises error."""
        with pytest.raises(ValidationError, match="Required field"):
            self.validator.parse_value(self.validated_field, None)

    def test_parse_empty_string_required_field_returns_empty_list(self):
        """Test that empty string for required field returns empty list."""
        result = self.validator.parse_value(self.validated_field, "")
        assert result == []

    def test_parse_valid_tags_required_field(self):
        """Test that valid tags work with required field."""
        result = self.validator.parse_value(self.validated_field, "python,javascript")
        assert result == ["python", "javascript"]


class TestTagsFieldDefault:
    """Tests for tags field default value handling."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for default value tests."""
        self.validator = TagsValidator(mock_space, mock_members)

    def test_none_uses_default_value(self):
        """Test that None value uses default."""
        default_tags = ["backend", "api"]
        field = SpaceField(id="tech", type=FieldType.TAGS, default=default_tags)
        validated = self.validator.validate_field_definition(field)
        result = self.validator.parse_value(validated, None)
        assert result == default_tags

    def test_empty_string_uses_none_not_default(self):
        """Test that empty string returns None, not default."""
        default_tags = ["backend", "api"]
        field = SpaceField(id="tech", type=FieldType.TAGS, required=False, default=default_tags)
        validated = self.validator.validate_field_definition(field)
        result = self.validator.parse_value(validated, "")
        assert result is None

    def test_explicit_value_overrides_default(self):
        """Test that explicit value overrides default."""
        default_tags = ["backend", "api"]
        field = SpaceField(id="tech", type=FieldType.TAGS, default=default_tags)
        validated = self.validator.validate_field_definition(field)
        result = self.validator.parse_value(validated, "frontend,ui")
        assert result == ["frontend", "ui"]

    def test_default_with_required_field(self):
        """Test that default works with required field when value is None."""
        default_tags = ["required", "tag"]
        field = SpaceField(id="must_have", type=FieldType.TAGS, required=True, default=default_tags)
        validated = self.validator.validate_field_definition(field)
        result = self.validator.parse_value(validated, None)
        assert result == default_tags


class TestTagsFieldEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for edge case tests."""
        self.validator = TagsValidator(mock_space, mock_members)
        self.field = SpaceField(id="tags", type=FieldType.TAGS, required=False)
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_parse_tags_with_special_characters(self):
        """Test parsing tags with special characters."""
        result = self.validator.parse_value(self.validated_field, "c++,node.js,asp.net")
        assert result == ["c++", "node.js", "asp.net"]

    def test_parse_tags_with_numbers(self):
        """Test parsing tags with numbers."""
        result = self.validator.parse_value(self.validated_field, "python3,web3,http2")
        assert result == ["python3", "web3", "http2"]

    def test_parse_tags_with_hyphens(self):
        """Test parsing tags with hyphens."""
        result = self.validator.parse_value(self.validated_field, "front-end,back-end,full-stack")
        assert result == ["front-end", "back-end", "full-stack"]

    def test_parse_tags_with_underscores(self):
        """Test parsing tags with underscores."""
        result = self.validator.parse_value(self.validated_field, "snake_case,test_driven,api_gateway")
        assert result == ["snake_case", "test_driven", "api_gateway"]

    def test_parse_single_tag_no_commas(self):
        """Test parsing a single tag without commas."""
        result = self.validator.parse_value(self.validated_field, "lonely-tag")
        assert result == ["lonely-tag"]

    def test_parse_many_tags(self):
        """Test parsing many tags."""
        tags_str = ",".join([f"tag{i}" for i in range(100)])
        result = self.validator.parse_value(self.validated_field, tags_str)
        assert len(result) == 100
        assert result[0] == "tag0"
        assert result[99] == "tag99"

    def test_parse_many_duplicate_tags(self):
        """Test parsing many duplicate tags."""
        tags_str = "python," * 50 + "javascript," * 50
        result = self.validator.parse_value(self.validated_field, tags_str)
        assert result == ["python", "javascript"]

    def test_parse_tags_case_sensitive(self):
        """Test that tag parsing is case-sensitive."""
        result = self.validator.parse_value(self.validated_field, "Python,python,PYTHON")
        assert result == ["Python", "python", "PYTHON"]

    def test_parse_tags_with_mixed_whitespace(self):
        """Test parsing tags with tabs and multiple spaces."""
        result = self.validator.parse_value(self.validated_field, "python,  javascript,\trust")
        assert result == ["python", "javascript", "rust"]
