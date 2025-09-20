"""Filter system for querying notes."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from spacenote.core.modules.field.models import FieldType, FieldValueType


class FilterOperator(StrEnum):
    """Query operators for filtering notes."""

    # Comparison
    EQ = "eq"  # equals
    NE = "ne"  # not equals

    # Text
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"

    # List/Set
    IN = "in"  # has any of
    NIN = "nin"  # has none of
    ALL = "all"  # has all

    # Numeric/Date
    GT = "gt"  # greater than
    GTE = "gte"  # greater than or equal
    LT = "lt"  # less than
    LTE = "lte"  # less than or equal


class FilterCondition(BaseModel):
    """Single filter condition for querying notes."""

    field: str = Field(..., description="Field name to filter on")
    operator: FilterOperator = Field(..., description="Comparison operator")
    value: FieldValueType = Field(..., description="Value to compare against")


class Filter(BaseModel):
    """Saved filter configuration for a space."""

    # Force unified schema for both input/output in OpenAPI to avoid Filter-Input/Output duplication
    model_config = ConfigDict(json_schema_mode_override="validation")

    name: str = Field(..., description="Unique filter identifier within the space")
    title: str = Field(..., description="Display name for the filter")
    description: str = Field("", description="Optional description of what this filter shows")
    conditions: list[FilterCondition] = Field(default_factory=list, description="Filter conditions (combined with AND)")
    sort: list[str] = Field(
        default_factory=list,
        description="Sort order - field names with optional '-' prefix for descending",
    )
    list_fields: list[str] = Field(default_factory=list, description="Fields to display in list view when this filter is active")


# Mapping of field types to their valid filter operators.
# This defines which operators can be used with each field type for filtering.
FIELD_TYPE_OPERATORS: dict[FieldType, set[FilterOperator]] = {
    FieldType.STRING: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.CONTAINS,
        FilterOperator.STARTSWITH,
        FilterOperator.ENDSWITH,
    },
    FieldType.MARKDOWN: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.CONTAINS,
        FilterOperator.STARTSWITH,
        FilterOperator.ENDSWITH,
    },
    FieldType.BOOLEAN: {
        FilterOperator.EQ,
        FilterOperator.NE,
    },
    FieldType.INT: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.GT,
        FilterOperator.GTE,
        FilterOperator.LT,
        FilterOperator.LTE,
    },
    FieldType.FLOAT: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.GT,
        FilterOperator.GTE,
        FilterOperator.LT,
        FilterOperator.LTE,
    },
    FieldType.DATETIME: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.GT,
        FilterOperator.GTE,
        FilterOperator.LT,
        FilterOperator.LTE,
    },
    FieldType.STRING_CHOICE: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.IN,
        FilterOperator.NIN,
    },
    FieldType.TAGS: {
        FilterOperator.EQ,
        FilterOperator.NE,
        FilterOperator.IN,
        FilterOperator.NIN,
        FilterOperator.ALL,
    },
    FieldType.USER: {
        FilterOperator.EQ,
        FilterOperator.NE,
    },
}


def get_operators_for_field_type(field_type: FieldType) -> list[FilterOperator]:
    """Get the list of valid operators for a given field type.

    Args:
        field_type: The field type to get operators for

    Returns:
        List of valid operators for the field type, sorted alphabetically
    """
    operators = FIELD_TYPE_OPERATORS.get(field_type, set())
    return sorted(operators, key=lambda x: x.value)
