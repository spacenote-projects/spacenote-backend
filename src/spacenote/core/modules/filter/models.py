"""Filter system for querying notes."""

from enum import StrEnum

from pydantic import BaseModel, Field

from spacenote.core.modules.field.models import FieldValueType


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

    name: str = Field(..., description="Unique filter identifier within the space")
    title: str = Field(..., description="Display name for the filter")
    description: str = Field("", description="Optional description of what this filter shows")
    conditions: list[FilterCondition] = Field(default_factory=list, description="Filter conditions (combined with AND)")
    sort: list[str] = Field(
        default_factory=list,
        description="Sort order - field names with optional '-' prefix for descending",
    )
    list_fields: list[str] = Field(default_factory=list, description="Fields to display in list view when this filter is active")
