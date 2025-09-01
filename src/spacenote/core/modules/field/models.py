"""Field system for custom note schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# Type for field option values (VALUES, MIN, MAX)
FieldOptionValueType = list[str] | int | float

# Type for actual field values in notes
FieldValueType = str | bool | list[str] | int | float | datetime | None


class FieldType(StrEnum):
    """Available field types for space schemas."""

    STRING = "string"
    MARKDOWN = "markdown"
    BOOLEAN = "boolean"
    STRING_CHOICE = "string_choice"  # Single select from predefined values
    TAGS = "tags"  # Free-form tags
    USER = "user"  # Reference to space member
    DATETIME = "datetime"
    INT = "int"
    FLOAT = "float"


class FieldOption(StrEnum):
    """Configuration options for field types."""

    VALUES = "values"  # list[str] for STRING_CHOICE
    MIN = "min"  # int/float for numeric types
    MAX = "max"  # int/float for numeric types


class SpaceField(BaseModel):
    """Field definition in a space schema."""

    name: str = Field(..., description="Field name (must be unique within space)")
    type: FieldType = Field(..., description="Field data type")
    required: bool = Field(False, description="Whether this field is required")
    options: dict[FieldOption, FieldOptionValueType] = Field(
        default_factory=dict,
        description="Field type-specific options (e.g., 'values' for string_choice, 'min'/'max' for numeric types)",
    )
    default: FieldValueType = Field(None, description="Default value for this field")
