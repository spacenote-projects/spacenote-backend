"""Field system for custom note schemas."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

# Type for field option values (VALUES, MIN, MAX, VALUE_MAPS, PREVIEWS)
FieldOptionValueType = list[str] | int | float | dict[str, dict[str, str]] | dict[str, dict[str, int]]

# Type for actual field values in notes
FieldValueType = str | bool | list[str] | int | float | datetime | UUID | None


class FieldType(StrEnum):
    """Available field types for space schemas."""

    STRING = "string"
    MARKDOWN = "markdown"
    BOOLEAN = "boolean"
    SELECT = "select"  # Single select from predefined values
    TAGS = "tags"  # Free-form tags
    USER = "user"  # Reference to space member
    DATETIME = "datetime"
    INT = "int"
    FLOAT = "float"
    IMAGE = "image"  # Reference to image attachment with previews


class FieldOption(StrEnum):
    """Configuration options for field types."""

    VALUES = "values"  # list[str] for SELECT
    MIN = "min"  # int/float for numeric types
    MAX = "max"  # int/float for numeric types
    VALUE_MAPS = "value_maps"  # dict[str, dict[str, str]] for SELECT metadata
    PREVIEWS = "previews"  # dict[str, dict] for IMAGE preview configurations


class SpecialValue(StrEnum):
    """Special values for fields."""

    ME = "$me"  # Represents the current logged-in user (for user fields)


class SpaceField(BaseModel):
    """Field definition in a space schema."""

    id: str = Field(..., description="Field identifier (must be unique within space)")
    type: FieldType = Field(..., description="Field data type")
    required: bool = Field(False, description="Whether this field is required")
    options: dict[FieldOption, FieldOptionValueType] = Field(
        default_factory=dict,
        description=(
            "Field type-specific options (e.g., 'values' for select, "
            "'min'/'max' for numeric types, 'value_maps' for select metadata)"
        ),
    )
    default: FieldValueType = Field(None, description="Default value for this field")
