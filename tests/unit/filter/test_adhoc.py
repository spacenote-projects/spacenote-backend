"""Tests for ad-hoc query parser."""

import urllib.parse
from uuid import uuid4

import pytest

from spacenote.core.modules.field.models import FieldType, SpaceField
from spacenote.core.modules.filter.adhoc import parse_adhoc_query
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User
from spacenote.errors import ValidationError


@pytest.fixture
def test_space():
    """Create a test space with various field types."""
    space_id = uuid4()
    return Space(
        id=space_id,
        slug="test",
        title="Test Space",
        members=[uuid4()],
        fields=[
            SpaceField(id="status", type=FieldType.STRING, required=False),
            SpaceField(id="priority", type=FieldType.INT, required=False),
            SpaceField(id="price", type=FieldType.FLOAT, required=False),
            SpaceField(id="active", type=FieldType.BOOLEAN, required=False),
            SpaceField(id="tags", type=FieldType.TAGS, required=False),
            SpaceField(id="assignee", type=FieldType.USER, required=False),
        ],
        filters=[],
    )


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(id=uuid4(), username="testuser", password_hash="hash", is_admin=False)


class TestBasicParsing:
    """Tests for basic query parsing."""

    def test_single_condition(self, test_space, test_user):
        """Test parsing single condition."""
        query = "status:eq:active"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].field == "status"
        assert conditions[0].operator == FilterOperator.EQ
        assert conditions[0].value == "active"

    def test_multiple_conditions(self, test_space, test_user):
        """Test parsing multiple conditions separated by commas."""
        query = "status:eq:active,priority:gte:5"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 2
        assert conditions[0].field == "status"
        assert conditions[0].operator == FilterOperator.EQ
        assert conditions[0].value == "active"
        assert conditions[1].field == "priority"
        assert conditions[1].operator == FilterOperator.GTE
        assert conditions[1].value == 5

    def test_empty_query_returns_empty_list(self, test_space, test_user):
        """Test that empty query returns empty list."""
        assert parse_adhoc_query("", test_space, [test_user]) == []
        assert parse_adhoc_query("   ", test_space, [test_user]) == []

    def test_whitespace_handling(self, test_space, test_user):
        """Test that whitespace around conditions is stripped."""
        query = " status:eq:active , priority:gte:5 "
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 2
        assert conditions[0].field == "status"
        assert conditions[1].field == "priority"

    def test_value_with_colon(self, test_space, test_user):
        """Test parsing value that contains colon character."""
        query = "status:eq:prefix:value"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == "prefix:value"


class TestArrayValues:
    """Tests for parsing array values."""

    def test_single_array_value(self, test_space, test_user):
        """Test parsing array with single value."""
        json_value = '["shopping"]'
        encoded = urllib.parse.quote(json_value)
        query = f"tags:in:{encoded}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].field == "tags"
        assert conditions[0].operator == FilterOperator.IN
        assert conditions[0].value == ["shopping"]

    def test_multiple_array_values(self, test_space, test_user):
        """Test parsing array with multiple values."""
        json_value = '["shopping","groceries","home"]'
        encoded = urllib.parse.quote(json_value)
        query = f"tags:in:{encoded}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == ["shopping", "groceries", "home"]

    def test_array_with_special_characters(self, test_space, test_user):
        """Test parsing array values containing special characters."""
        json_value = '["item|pipe","item,comma","item:colon"]'
        encoded = urllib.parse.quote(json_value)
        query = f"tags:in:{encoded}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == ["item|pipe", "item,comma", "item:colon"]

    def test_nin_operator_with_array(self, test_space, test_user):
        """Test NIN operator with array values."""
        json_value = '["archived","deleted"]'
        encoded = urllib.parse.quote(json_value)
        query = f"tags:nin:{encoded}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].operator == FilterOperator.NIN
        assert conditions[0].value == ["archived", "deleted"]

    def test_all_operator_with_array(self, test_space, test_user):
        """Test ALL operator with array values."""
        json_value = '["urgent","bug"]'
        encoded = urllib.parse.quote(json_value)
        query = f"tags:all:{encoded}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].operator == FilterOperator.ALL
        assert conditions[0].value == ["urgent", "bug"]


class TestSystemFields:
    """Tests for system field handling."""

    def test_number_field(self, test_space, test_user):
        """Test filtering by system field 'number'."""
        query = "number:gt:100"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].field == "number"
        assert conditions[0].operator == FilterOperator.GT
        assert conditions[0].value == 100

    def test_user_id_field_with_special_value(self, test_space, test_user):
        """Test user_id field with $me special value."""
        query = "user_id:eq:$me"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].field == "user_id"
        assert conditions[0].value == "$me"

    def test_created_at_field(self, test_space, test_user):
        """Test filtering by created_at system field."""
        query = "created_at:gte:2024-01-01"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].field == "created_at"
        assert conditions[0].operator == FilterOperator.GTE


class TestValueTypeParsing:
    """Tests for automatic value type parsing."""

    def test_null_value_parsing(self, test_space, test_user):
        """Test that 'null' string is parsed as None."""
        query = "status:eq:null"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value is None

    def test_boolean_true_parsing(self, test_space, test_user):
        """Test that 'true' string is parsed as boolean True."""
        query = "active:eq:true"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value is True

    def test_boolean_false_parsing(self, test_space, test_user):
        """Test that 'false' string is parsed as boolean False."""
        query = "active:eq:false"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value is False

    def test_integer_parsing(self, test_space, test_user):
        """Test that numeric strings are parsed as integers."""
        query = "priority:gte:5"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == 5
        assert isinstance(conditions[0].value, int)

    def test_float_parsing(self, test_space, test_user):
        """Test that decimal strings are parsed as floats."""
        query = "price:gte:9.99"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == 9.99
        assert isinstance(conditions[0].value, float)

    def test_string_value_not_parsed(self, test_space, test_user):
        """Test that non-special strings remain as strings."""
        query = "status:eq:active"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == "active"
        assert isinstance(conditions[0].value, str)


class TestURLEncoding:
    """Tests for URL encoding handling."""

    def test_url_encoded_spaces(self, test_space, test_user):
        """Test that URL-encoded spaces are decoded correctly."""
        query = "status:contains:hello%20world"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == "hello world"

    def test_url_encoded_special_characters(self, test_space, test_user):
        """Test decoding of various URL-encoded special characters."""
        encoded_value = urllib.parse.quote("test & value")
        query = f"status:contains:{encoded_value}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == "test & value"

    def test_url_encoded_json_array(self, test_space, test_user):
        """Test that URL-encoded JSON arrays are decoded and parsed."""
        json_array = '["shopping","groceries"]'
        encoded = urllib.parse.quote(json_array)
        query = f"tags:in:{encoded}"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 1
        assert conditions[0].value == ["shopping", "groceries"]


class TestOperators:
    """Tests for different operator types."""

    def test_comparison_operators(self, test_space, test_user):
        """Test all comparison operators."""
        test_cases = [
            ("priority:gt:5", FilterOperator.GT),
            ("priority:gte:5", FilterOperator.GTE),
            ("priority:lt:10", FilterOperator.LT),
            ("priority:lte:10", FilterOperator.LTE),
            ("priority:eq:5", FilterOperator.EQ),
            ("priority:ne:0", FilterOperator.NE),
        ]

        for query, expected_op in test_cases:
            conditions = parse_adhoc_query(query, test_space, [test_user])
            assert conditions[0].operator == expected_op

    def test_text_operators(self, test_space, test_user):
        """Test text search operators."""
        test_cases = [
            ("status:contains:test", FilterOperator.CONTAINS),
            ("status:startswith:active", FilterOperator.STARTSWITH),
            ("status:endswith:done", FilterOperator.ENDSWITH),
        ]

        for query, expected_op in test_cases:
            conditions = parse_adhoc_query(query, test_space, [test_user])
            assert conditions[0].operator == expected_op


class TestErrorCases:
    """Tests for error handling."""

    def test_invalid_field_name(self, test_space, test_user):
        """Test that invalid field name raises ValidationError."""
        query = "nonexistent:eq:value"
        with pytest.raises(ValidationError, match="Field 'nonexistent' not found in space"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_invalid_operator(self, test_space, test_user):
        """Test that invalid operator raises ValidationError."""
        query = "status:invalid:value"
        with pytest.raises(ValidationError, match="Unknown operator 'invalid'"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_incompatible_operator_for_field_type(self, test_space, test_user):
        """Test that incompatible operator for field type raises ValidationError."""
        query = "priority:contains:text"
        with pytest.raises(ValidationError, match="not valid for field 'priority' of type"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_malformed_syntax_missing_value(self, test_space, test_user):
        """Test that malformed syntax raises ValidationError."""
        query = "status:eq"
        with pytest.raises(ValidationError, match="Invalid query syntax"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_malformed_syntax_missing_operator(self, test_space, test_user):
        """Test that missing operator raises ValidationError."""
        query = "status"
        with pytest.raises(ValidationError, match="Invalid query syntax"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_invalid_json_array(self, test_space, test_user):
        """Test that invalid JSON array raises ValidationError."""
        invalid_json = '["unclosed'
        encoded = urllib.parse.quote(invalid_json)
        query = f"tags:in:{encoded}"
        with pytest.raises(ValidationError, match="Invalid JSON array"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_non_array_value_for_in_operator(self, test_space, test_user):
        """Test that non-array value for IN operator raises ValidationError."""
        query = "tags:in:notanarray"
        with pytest.raises(ValidationError, match="Invalid JSON array"):
            parse_adhoc_query(query, test_space, [test_user])

    def test_array_operator_on_non_array_field(self, test_space, test_user):
        """Test that using array operator on non-array field raises ValidationError."""
        json_value = '["value1","value2"]'
        encoded = urllib.parse.quote(json_value)
        query = f"status:in:{encoded}"
        # Should fail because IN operator is not valid for STRING field type
        with pytest.raises(ValidationError, match="not valid for field 'status' of type"):
            parse_adhoc_query(query, test_space, [test_user])


class TestComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_multiple_conditions_different_types(self, test_space, test_user):
        """Test query with multiple conditions of different types."""
        json_value = '["urgent"]'
        encoded = urllib.parse.quote(json_value)
        query = f"status:eq:active,priority:gte:5,tags:in:{encoded},active:eq:true"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 4
        assert conditions[0].field == "status"
        assert conditions[0].value == "active"
        assert conditions[1].field == "priority"
        assert conditions[1].value == 5
        assert conditions[2].field == "tags"
        assert conditions[2].value == ["urgent"]
        assert conditions[3].field == "active"
        assert conditions[3].value is True

    def test_combining_system_and_custom_fields(self, test_space, test_user):
        """Test query combining system and custom fields."""
        query = "user_id:eq:$me,status:eq:active,number:gt:100"
        conditions = parse_adhoc_query(query, test_space, [test_user])

        assert len(conditions) == 3
        assert conditions[0].field == "user_id"
        assert conditions[1].field == "status"
        assert conditions[2].field == "number"
