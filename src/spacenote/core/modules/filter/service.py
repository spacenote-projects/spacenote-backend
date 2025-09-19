from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldType, SpaceField
from spacenote.core.modules.filter.models import Filter, FilterOperator
from spacenote.core.modules.filter.validators import validate_filter_value
from spacenote.core.modules.note.models import NOTE_SYSTEM_FIELDS
from spacenote.errors import ValidationError


class FilterService(Service):
    """Service for filter validation and management."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    def _get_system_field_definition(self, field_name: str) -> SpaceField | None:
        """Get virtual field definition for system fields."""
        if field_name == "number":
            return SpaceField(name="number", type=FieldType.INT, required=True)
        if field_name == "created_at":
            return SpaceField(name="created_at", type=FieldType.DATETIME, required=True)
        if field_name == "author":
            return SpaceField(name="author", type=FieldType.USER, required=True)
        return None

    async def add_filter_to_space(self, space_id: UUID, filter: Filter) -> None:
        """Add a filter to a space with validation.

        Args:
            space_id: The space to add the filter to
            filter: Filter definition to validate, normalize, and add to the space

        Raises:
            ValidationError: If filter already exists or is invalid
            NotFoundError: If space not found
        """
        space = self.core.services.space.get_space(space_id)

        # Validate filter name is unique
        if space.get_filter(filter.name) is not None:
            raise ValidationError(f"Filter '{filter.name}' already exists in space")

        # Validate filter name format (alphanumeric + underscores)
        if not filter.name or not filter.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid filter name: {filter.name}")

        # Validate all fields in conditions exist in the space or are system fields
        for condition in filter.conditions:
            field = space.get_field(condition.field)
            if field is None:
                # Check if it's a system field
                field = self._get_system_field_definition(condition.field)
                if field is None:
                    raise ValidationError(f"Field '{condition.field}' referenced in filter condition does not exist in space")

            # Validate operator is compatible with field type
            self._validate_operator_for_field_type(field.type, condition.operator, condition.field)

            # Validate the value is compatible with the field type and operator
            validate_filter_value(field, condition.operator, condition.value)

        # Validate all fields in list_fields exist in the space or are system fields
        for field_name in filter.list_fields:
            if field_name not in NOTE_SYSTEM_FIELDS and space.get_field(field_name) is None:
                raise ValidationError(f"Field '{field_name}' in list_fields does not exist in space")

        # Validate all fields in sort exist in the space or are system fields
        for sort_field in filter.sort:
            # Remove '-' prefix if present for descending sort
            field_name = sort_field.lstrip("-")
            if field_name not in NOTE_SYSTEM_FIELDS and space.get_field(field_name) is None:
                raise ValidationError(f"Field '{field_name}' in sort does not exist in space")

        # Add filter to space
        spaces_collection = self.database["spaces"]
        await spaces_collection.update_one({"_id": space_id}, {"$push": {"filters": filter.model_dump()}})
        await self.core.services.space.update_space_cache(space_id)

    def _validate_operator_for_field_type(self, field_type: FieldType, operator: FilterOperator, field_name: str) -> None:
        """Validate that an operator is compatible with a field type."""
        # Text operators - valid for string, markdown
        text_operators = {
            FilterOperator.EQ,
            FilterOperator.NE,
            FilterOperator.CONTAINS,
            FilterOperator.STARTSWITH,
            FilterOperator.ENDSWITH,
        }

        # List operators - valid for tags
        list_operators = {FilterOperator.IN, FilterOperator.NIN, FilterOperator.ALL}

        # Numeric/date operators - valid for int, float, datetime
        comparison_operators = {FilterOperator.GT, FilterOperator.GTE, FilterOperator.LT, FilterOperator.LTE}

        # Universal operators - valid for all types
        universal_operators = {FilterOperator.EQ, FilterOperator.NE}

        if field_type in (FieldType.STRING, FieldType.MARKDOWN):
            valid_operators = text_operators
        elif field_type == FieldType.TAGS:
            valid_operators = list_operators | universal_operators
        elif field_type in (FieldType.INT, FieldType.FLOAT, FieldType.DATETIME):
            valid_operators = comparison_operators | universal_operators
        elif field_type == FieldType.BOOLEAN:
            valid_operators = universal_operators
        elif field_type == FieldType.STRING_CHOICE:
            valid_operators = universal_operators | {FilterOperator.IN, FilterOperator.NIN}
        elif field_type == FieldType.USER:
            valid_operators = universal_operators
        else:
            raise ValidationError(f"Unknown field type: {field_type}")

        if operator not in valid_operators:
            raise ValidationError(f"Operator '{operator}' is not valid for field '{field_name}' of type '{field_type}'")

    async def remove_filter_from_space(self, space_id: UUID, filter_name: str) -> None:
        """Remove a filter from a space.

        Args:
            space_id: The space to remove the filter from
            filter_name: The name of the filter to remove

        Raises:
            NotFoundError: If space or filter not found
        """
        raise NotImplementedError
