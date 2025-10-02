import logging
from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldType, SpaceField
from spacenote.core.modules.filter.models import FIELD_TYPE_OPERATORS, Filter
from spacenote.core.modules.filter.query_builder import build_mongo_query, build_mongo_sort
from spacenote.core.modules.filter.validators import validate_filter_value
from spacenote.core.modules.note.models import NOTE_SYSTEM_FIELDS
from spacenote.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

SYSTEM_FIELD_DEFINITIONS: dict[str, SpaceField] = {
    "number": SpaceField(id="number", type=FieldType.INT, required=True),
    "created_at": SpaceField(id="created_at", type=FieldType.DATETIME, required=True),
    "user_id": SpaceField(id="user_id", type=FieldType.USER, required=True),
}


class FilterService(Service):
    """Service for filter validation and management."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

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

        # Validate filter id is unique
        if space.get_filter(filter.id) is not None:
            raise ValidationError(f"Filter '{filter.id}' already exists in space")

        # Validate filter id format (alphanumeric + underscores + hyphens)
        if not filter.id or not filter.id.replace("_", "").replace("-", "").isalnum():
            raise ValidationError(f"Invalid filter id: {filter.id}")

        # Validate all fields in conditions exist in the space or are system fields
        for condition in filter.conditions:
            field = space.get_field(condition.field)
            if field is None:
                # Check if it's a system field
                field = SYSTEM_FIELD_DEFINITIONS.get(condition.field)
                if field is None:
                    raise ValidationError(f"Field '{condition.field}' referenced in filter condition does not exist in space")

            # Validate operator is compatible with field type
            valid_operators = FIELD_TYPE_OPERATORS.get(field.type)
            if valid_operators is None:
                raise ValidationError(f"Unknown field type: {field.type}")
            if condition.operator not in valid_operators:
                raise ValidationError(
                    f"Operator '{condition.operator}' is not valid for field '{condition.field}' of type '{field.type}'"
                )

            # Validate the value is compatible with the field type and operator
            validate_filter_value(field, condition.operator, condition.value)

        # Validate all fields in list_fields exist in the space or are system fields
        for field_id in filter.list_fields:
            if field_id not in NOTE_SYSTEM_FIELDS and space.get_field(field_id) is None:
                raise ValidationError(f"Field '{field_id}' in list_fields does not exist in space")

        # Validate all fields in sort exist in the space or are system fields
        for sort_field in filter.sort:
            # Remove '-' prefix if present for descending sort
            field_id = sort_field.lstrip("-")
            if field_id not in NOTE_SYSTEM_FIELDS and space.get_field(field_id) is None:
                raise ValidationError(f"Field '{field_id}' in sort does not exist in space")

        # Add filter to space
        spaces_collection = self.database["spaces"]
        await spaces_collection.update_one({"_id": space_id}, {"$push": {"filters": filter.model_dump()}})
        await self.core.services.space.update_space_cache(space_id)

    async def remove_filter_from_space(self, space_id: UUID, filter_id: str) -> None:
        """Remove a filter from a space.

        Args:
            space_id: The space to remove the filter from
            filter_id: The id of the filter to remove

        Raises:
            NotFoundError: If space or filter not found
        """
        space = self.core.services.space.get_space(space_id)

        # Check if filter exists
        if space.get_filter(filter_id) is None:
            raise NotFoundError(f"Filter '{filter_id}' not found in space")

        # Remove filter from space
        spaces_collection = self.database["spaces"]
        await spaces_collection.update_one({"_id": space_id}, {"$pull": {"filters": {"id": filter_id}}})
        await self.core.services.space.update_space_cache(space_id)

    def build_mongo_query(self, space_id: UUID, filter_id: str, current_user_id: UUID | None = None) -> dict[str, Any]:
        """Build MongoDB query document from a filter.

        Args:
            space_id: The space ID containing the filter
            filter_id: The id of the filter to use
            current_user_id: The ID of the current logged-in user (optional, for $me substitution)

        Returns:
            MongoDB query document with filter conditions

        Raises:
            NotFoundError: If space or filter not found
        """
        space = self.core.services.space.get_space(space_id)
        filter_def = space.get_filter(filter_id)
        if filter_def is None:
            raise NotFoundError(f"Filter '{filter_id}' not found in space")

        field_definitions = {}
        valid_conditions = []
        for condition in filter_def.conditions:
            field = space.get_field(condition.field)
            if field is None:
                field = SYSTEM_FIELD_DEFINITIONS.get(condition.field)
            if field is not None:
                field_definitions[condition.field] = field
                valid_conditions.append(condition)
            else:
                logger.warning(
                    "Field '%s' in filter '%s' not found in space %s - likely deleted after filter creation. "
                    "Skipping condition with operator '%s' and value '%s'.",
                    condition.field,
                    filter_id,
                    space_id,
                    condition.operator,
                    condition.value,
                )

        return build_mongo_query(valid_conditions, field_definitions, space_id, current_user_id)

    def build_mongo_sort(self, space_id: UUID, filter_id: str) -> list[tuple[str, int]]:
        """Build MongoDB sort specification from a filter.

        Args:
            space_id: The space ID containing the filter
            filter_id: The id of the filter to use

        Returns:
            List of (field, direction) tuples for sorting

        Raises:
            NotFoundError: If space or filter not found
        """
        space = self.core.services.space.get_space(space_id)
        filter_def = space.get_filter(filter_id)
        if filter_def is None:
            raise NotFoundError(f"Filter '{filter_id}' not found in space")

        return build_mongo_sort(filter_def.sort)
