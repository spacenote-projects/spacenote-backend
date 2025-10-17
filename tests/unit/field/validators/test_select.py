"""Tests for SELECT field validator."""

import pytest

from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.core.modules.field.validators import SelectValidator
from spacenote.errors import ValidationError


class TestSelectValueMaps:
    """Tests for value_maps feature in SELECT fields."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for all tests in this class."""
        self.validator = SelectValidator(mock_space, mock_members)

    def test_valid_value_maps_with_multiple_properties(self):
        """Test that valid value_maps with multiple properties are accepted."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={
                FieldOption.VALUES: ["new", "in_progress", "done"],
                FieldOption.VALUE_MAPS: {
                    "color": {"new": "#gray", "in_progress": "#blue", "done": "#green"},
                    "icon": {"new": "plus", "in_progress": "clock", "done": "check"},
                    "weight": {"new": "1", "in_progress": "2", "done": "3"},
                },
            },
        )
        result = self.validator.validate_field_definition(field)
        assert result.options[FieldOption.VALUE_MAPS] == field.options[FieldOption.VALUE_MAPS]
        assert len(result.options[FieldOption.VALUE_MAPS]) == 3

    def test_empty_value_maps_allowed(self):
        """Test that empty value_maps dictionary is valid."""
        field = SpaceField(
            id="priority", type=FieldType.SELECT, options={FieldOption.VALUES: ["low", "high"], FieldOption.VALUE_MAPS: {}}
        )
        result = self.validator.validate_field_definition(field)
        assert result.options[FieldOption.VALUE_MAPS] == {}

    def test_no_value_maps_is_optional(self):
        """Test that value_maps is completely optional."""
        field = SpaceField(id="choice", type=FieldType.SELECT, options={FieldOption.VALUES: ["yes", "no", "maybe"]})
        result = self.validator.validate_field_definition(field)
        assert FieldOption.VALUE_MAPS not in result.options

    def test_missing_keys_in_value_map_raises_error(self):
        """Test that missing keys in a value_map raises ValidationError."""
        field = SpaceField(
            id="severity",
            type=FieldType.SELECT,
            options={
                FieldOption.VALUES: ["low", "medium", "high"],
                FieldOption.VALUE_MAPS: {
                    "color": {"low": "#green", "high": "#red"}  # missing 'medium'
                },
            },
        )
        with pytest.raises(ValidationError, match="missing entries for: medium"):
            self.validator.validate_field_definition(field)

    def test_extra_keys_in_value_map_raises_error(self):
        """Test that extra keys in a value_map raises ValidationError."""
        field = SpaceField(
            id="level",
            type=FieldType.SELECT,
            options={
                FieldOption.VALUES: ["info", "warning", "error"],
                FieldOption.VALUE_MAPS: {
                    "color": {
                        "info": "#blue",
                        "warning": "#yellow",
                        "error": "#red",
                        "critical": "#purple",  # extra key
                    }
                },
            },
        )
        with pytest.raises(ValidationError, match="has unknown keys: critical"):
            self.validator.validate_field_definition(field)

    def test_inconsistent_keys_across_maps_raises_error(self):
        """Test that each map must have all required keys."""
        field = SpaceField(
            id="priority",
            type=FieldType.SELECT,
            options={
                FieldOption.VALUES: ["low", "medium", "high"],
                FieldOption.VALUE_MAPS: {
                    "color": {"low": "#green", "medium": "#yellow", "high": "#red"},
                    "weight": {"low": "1", "high": "10"},  # missing 'medium'
                },
            },
        )
        with pytest.raises(ValidationError, match="missing entries for: medium"):
            self.validator.validate_field_definition(field)

    def test_single_value_map_with_all_keys(self):
        """Test a single value_map with all required keys."""
        field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            options={
                FieldOption.VALUES: ["active", "inactive"],
                FieldOption.VALUE_MAPS: {"label": {"active": "Active", "inactive": "Inactive"}},
            },
        )
        result = self.validator.validate_field_definition(field)
        assert "label" in result.options[FieldOption.VALUE_MAPS]
        assert len(result.options[FieldOption.VALUE_MAPS]["label"]) == 2


class TestSelectFieldParsing:
    """Tests for SELECT field value parsing with value_maps."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator and field for parsing tests."""
        self.validator = SelectValidator(mock_space, mock_members)
        self.field = SpaceField(
            id="status",
            type=FieldType.SELECT,
            required=True,
            options={
                FieldOption.VALUES: ["new", "active", "closed"],
                FieldOption.VALUE_MAPS: {"color": {"new": "#green", "active": "#blue", "closed": "#gray"}},
            },
        )
        self.validated_field = self.validator.validate_field_definition(self.field)

    def test_value_maps_does_not_affect_valid_choice_parsing(self):
        """Test that value_maps doesn't interfere with valid choice parsing."""
        assert self.validator.parse_value(self.validated_field, "new") == "new"
        assert self.validator.parse_value(self.validated_field, "active") == "active"
        assert self.validator.parse_value(self.validated_field, "closed") == "closed"

    def test_invalid_choice_rejected_with_value_maps(self):
        """Test that invalid choices are still rejected when value_maps present."""
        with pytest.raises(ValidationError, match="Invalid choice"):
            self.validator.parse_value(self.validated_field, "invalid")

    def test_required_field_with_value_maps_cannot_be_none(self):
        """Test that required fields with value_maps still require values."""
        with pytest.raises(ValidationError, match="Required field"):
            self.validator.parse_value(self.validated_field, None)

    def test_optional_field_with_value_maps_can_be_empty(self):
        """Test that optional fields with value_maps can be empty."""
        optional_field = SpaceField(
            id="priority",
            type=FieldType.SELECT,
            required=False,
            options={FieldOption.VALUES: ["low", "high"], FieldOption.VALUE_MAPS: {"color": {"low": "#green", "high": "#red"}}},
        )
        validated = self.validator.validate_field_definition(optional_field)
        assert self.validator.parse_value(validated, "") is None
        assert self.validator.parse_value(validated, None) is None


class TestSelectComplexScenarios:
    """Tests for complex real-world scenarios with value_maps."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_space, mock_members):
        """Set up validator for complex scenario tests."""
        self.validator = SelectValidator(mock_space, mock_members)

    def test_task_management_system_with_rich_metadata(self):
        """Test a realistic task management system with multiple value_maps."""
        task_field = SpaceField(
            id="task_status",
            type=FieldType.SELECT,
            required=True,
            options={
                FieldOption.VALUES: ["todo", "in_progress", "review", "done", "blocked"],
                FieldOption.VALUE_MAPS: {
                    "color": {"todo": "#gray", "in_progress": "#blue", "review": "#yellow", "done": "#green", "blocked": "#red"},
                    "icon": {
                        "todo": "circle-outline",
                        "in_progress": "progress-clock",
                        "review": "eye",
                        "done": "check-circle",
                        "blocked": "x-octagon",
                    },
                    "progress_percent": {"todo": "0", "in_progress": "50", "review": "75", "done": "100", "blocked": "0"},
                    "ui_label": {
                        "todo": "To Do",
                        "in_progress": "In Progress",
                        "review": "Under Review",
                        "done": "Completed",
                        "blocked": "Blocked",
                    },
                },
            },
        )

        result = self.validator.validate_field_definition(task_field)
        value_maps = result.options.get(FieldOption.VALUE_MAPS)

        # Verify structure
        assert isinstance(value_maps, dict)
        assert len(value_maps) == 4

        # Verify each map has all 5 status values
        for map_data in value_maps.values():
            assert len(map_data) == 5
            assert all(status in map_data for status in ["todo", "in_progress", "review", "done", "blocked"])

    def test_priority_system_with_semantic_mappings(self):
        """Test a priority system with semantic value mappings."""
        priority_field = SpaceField(
            id="priority",
            type=FieldType.SELECT,
            options={
                FieldOption.VALUES: ["p0", "p1", "p2", "p3"],
                FieldOption.VALUE_MAPS: {
                    "label": {
                        "p0": "Critical - Drop Everything",
                        "p1": "High - Do Today",
                        "p2": "Medium - Do This Week",
                        "p3": "Low - Nice to Have",
                    },
                    "sla_hours": {"p0": "2", "p1": "24", "p2": "72", "p3": "168"},
                    "color": {"p0": "#FF0000", "p1": "#FF6600", "p2": "#FFCC00", "p3": "#00CC00"},
                },
            },
        )

        result = self.validator.validate_field_definition(priority_field)
        value_maps = result.options[FieldOption.VALUE_MAPS]

        # Verify semantic mappings are preserved
        assert value_maps["label"]["p0"] == "Critical - Drop Everything"
        assert value_maps["sla_hours"]["p1"] == "24"
        assert value_maps["color"]["p3"] == "#00CC00"
