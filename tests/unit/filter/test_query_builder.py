"""Tests for filter query builder pure functions."""

from uuid import UUID

import pytest

from spacenote.core.modules.field.models import FieldType, SpaceField, SpecialValue
from spacenote.core.modules.filter.models import FilterCondition, FilterOperator
from spacenote.core.modules.filter.query_builder import (
    build_condition_query,
    build_mongo_query,
    build_mongo_sort,
    get_field_path,
    resolve_special_values,
)
from spacenote.errors import ValidationError


class TestGetFieldPath:
    """Tests for get_field_path function."""

    def test_system_field_returns_direct_path(self):
        """Test that system fields return their ID directly."""
        assert get_field_path("number") == "number"
        assert get_field_path("created_at") == "created_at"
        assert get_field_path("user_id") == "user_id"

    def test_custom_field_returns_prefixed_path(self):
        """Test that custom fields are prefixed with 'fields.'"""
        assert get_field_path("title") == "fields.title"
        assert get_field_path("status") == "fields.status"


class TestBuildConditionQuery:
    """Tests for build_condition_query function."""

    def test_null_value_with_eq_operator(self):
        """Test null value with EQ operator."""
        assert build_condition_query(FilterOperator.EQ, None) == {"$eq": None}

    def test_null_value_with_ne_operator(self):
        """Test null value with NE operator."""
        assert build_condition_query(FilterOperator.NE, None) == {"$ne": None}

    def test_eq_operator_returns_dict(self):
        """Test EQ operator returns dict with $eq."""
        assert build_condition_query(FilterOperator.EQ, "test") == {"$eq": "test"}
        assert build_condition_query(FilterOperator.EQ, 42) == {"$eq": 42}

    def test_comparison_operators(self):
        """Test numeric comparison operators."""
        assert build_condition_query(FilterOperator.NE, 5) == {"$ne": 5}
        assert build_condition_query(FilterOperator.GT, 10) == {"$gt": 10}
        assert build_condition_query(FilterOperator.GTE, 10) == {"$gte": 10}
        assert build_condition_query(FilterOperator.LT, 20) == {"$lt": 20}
        assert build_condition_query(FilterOperator.LTE, 20) == {"$lte": 20}

    def test_list_operators(self):
        """Test list-based operators."""
        assert build_condition_query(FilterOperator.IN, ["a", "b"]) == {"$in": ["a", "b"]}
        assert build_condition_query(FilterOperator.NIN, ["x", "y"]) == {"$nin": ["x", "y"]}
        assert build_condition_query(FilterOperator.ALL, ["tag1", "tag2"]) == {"$all": ["tag1", "tag2"]}

    def test_text_search_operators(self):
        """Test text search operators generate regex queries."""
        assert build_condition_query(FilterOperator.CONTAINS, "test") == {"$regex": "test", "$options": "i"}
        assert build_condition_query(FilterOperator.STARTSWITH, "prefix") == {"$regex": "^prefix", "$options": "i"}
        assert build_condition_query(FilterOperator.ENDSWITH, "suffix") == {"$regex": "suffix$", "$options": "i"}


class TestBuildMongoSort:
    """Tests for build_mongo_sort function."""

    def test_empty_sort_returns_default(self):
        """Test empty sort list returns default number descending."""
        assert build_mongo_sort([]) == [("number", -1)]

    def test_ascending_sort(self):
        """Test ascending sort on field."""
        assert build_mongo_sort(["title"]) == [("fields.title", 1)]

    def test_descending_sort(self):
        """Test descending sort with '-' prefix."""
        assert build_mongo_sort(["-created_at"]) == [("created_at", -1)]

    def test_multiple_sort_fields(self):
        """Test sorting by multiple fields."""
        result = build_mongo_sort(["status", "-created_at", "title"])
        expected = [("fields.status", 1), ("created_at", -1), ("fields.title", 1)]
        assert result == expected

    def test_system_and_custom_fields_mixed(self):
        """Test sort with both system and custom fields."""
        result = build_mongo_sort(["-number", "status"])
        assert result == [("number", -1), ("fields.status", 1)]


class TestResolveSpecialValues:
    """Tests for resolve_special_values function."""

    def test_non_special_value_returns_unchanged(self):
        """Test that regular values pass through unchanged."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        assert resolve_special_values("regular", FieldType.STRING, user_id) == "regular"
        assert resolve_special_values(42, FieldType.INT, None) == 42

    def test_me_value_with_user_field_resolves_to_user_id(self):
        """Test $me gets resolved to current user ID for USER fields."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        result = resolve_special_values(SpecialValue.ME, FieldType.USER, user_id)
        assert result == user_id

    def test_me_value_without_user_context_raises_error(self):
        """Test $me without user context raises ValidationError."""
        with pytest.raises(ValidationError, match="without a logged-in user context"):
            resolve_special_values(SpecialValue.ME, FieldType.USER, None)

    def test_me_value_on_non_user_field_returns_unchanged(self):
        """Test $me on non-USER field is not resolved."""
        result = resolve_special_values(SpecialValue.ME, FieldType.STRING, None)
        assert result == SpecialValue.ME


class TestBuildMongoQuery:
    """Tests for build_mongo_query function."""

    def test_empty_conditions_returns_space_query(self):
        """Test query with no conditions returns only space_id filter."""
        space_id = UUID("12345678-1234-5678-1234-567812345678")
        result = build_mongo_query([], {}, space_id)
        assert result == {"space_id": space_id}

    def test_single_eq_condition(self):
        """Test single equality condition."""
        space_id = UUID("12345678-1234-5678-1234-567812345678")
        conditions = [FilterCondition(field="status", operator=FilterOperator.EQ, value="active")]
        field_defs = {"status": SpaceField(id="status", type=FieldType.STRING, required=True)}

        result = build_mongo_query(conditions, field_defs, space_id)
        assert result == {"space_id": space_id, "fields.status": {"$eq": "active"}}

    def test_multiple_conditions_on_different_fields(self):
        """Test multiple conditions on different fields."""
        space_id = UUID("12345678-1234-5678-1234-567812345678")
        conditions = [
            FilterCondition(field="status", operator=FilterOperator.EQ, value="done"),
            FilterCondition(field="priority", operator=FilterOperator.GT, value=5),
        ]
        field_defs = {
            "status": SpaceField(id="status", type=FieldType.STRING, required=True),
            "priority": SpaceField(id="priority", type=FieldType.INT, required=True),
        }

        result = build_mongo_query(conditions, field_defs, space_id)
        assert result["space_id"] == space_id
        assert result["fields.status"] == {"$eq": "done"}
        assert result["fields.priority"] == {"$gt": 5}

    def test_multiple_conditions_on_same_field_uses_and(self):
        """Test multiple conditions on same field uses $and operator."""
        space_id = UUID("12345678-1234-5678-1234-567812345678")
        conditions = [
            FilterCondition(field="count", operator=FilterOperator.GT, value=5),
            FilterCondition(field="count", operator=FilterOperator.LT, value=20),
        ]
        field_defs = {"count": SpaceField(id="count", type=FieldType.INT, required=True)}

        result = build_mongo_query(conditions, field_defs, space_id)
        assert result["space_id"] == space_id
        assert "$and" in result
        assert {"fields.count": {"$gt": 5}} in result["$and"]
        assert {"fields.count": {"$lt": 20}} in result["$and"]

    def test_user_field_with_me_value_resolves(self):
        """Test USER field with $me special value gets resolved."""
        space_id = UUID("12345678-1234-5678-1234-567812345678")
        user_id = UUID("87654321-4321-8765-4321-876543218765")
        conditions = [FilterCondition(field="assignee", operator=FilterOperator.EQ, value=SpecialValue.ME)]
        field_defs = {"assignee": SpaceField(id="assignee", type=FieldType.USER, required=False)}

        result = build_mongo_query(conditions, field_defs, space_id, user_id)
        assert result["fields.assignee"] == {"$eq": user_id}

    def test_system_field_in_query(self):
        """Test that system fields are not prefixed with 'fields.'"""
        space_id = UUID("12345678-1234-5678-1234-567812345678")
        conditions = [FilterCondition(field="number", operator=FilterOperator.GT, value=100)]
        field_defs = {"number": SpaceField(id="number", type=FieldType.INT, required=True)}

        result = build_mongo_query(conditions, field_defs, space_id)
        assert result["number"] == {"$gt": 100}
