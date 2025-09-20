from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldType, SpaceField
from spacenote.core.modules.filter.models import FIELD_TYPE_OPERATORS, Filter, FilterOperator
from spacenote.core.modules.filter.validators import validate_filter_value
from spacenote.core.modules.note.models import NOTE_SYSTEM_FIELDS
from spacenote.errors import NotFoundError, ValidationError


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

    async def remove_filter_from_space(self, space_id: UUID, filter_name: str) -> None:
        """Remove a filter from a space.

        Args:
            space_id: The space to remove the filter from
            filter_name: The name of the filter to remove

        Raises:
            NotFoundError: If space or filter not found
        """
        space = self.core.services.space.get_space(space_id)

        # Check if filter exists
        if space.get_filter(filter_name) is None:
            raise NotFoundError(f"Filter '{filter_name}' not found in space")

        # Remove filter from space
        spaces_collection = self.database["spaces"]
        await spaces_collection.update_one({"_id": space_id}, {"$pull": {"filters": {"name": filter_name}}})
        await self.core.services.space.update_space_cache(space_id)

    def build_mongo_query(self, space_id: UUID, filter_name: str) -> dict[str, Any]:
        """Build MongoDB query document from a filter.

        Args:
            space_id: The space ID containing the filter
            filter_name: The name of the filter to use

        Returns:
            MongoDB query document with filter conditions

        Raises:
            NotFoundError: If space or filter not found
        """
        space = self.core.services.space.get_space(space_id)
        filter_def = space.get_filter(filter_name)
        if filter_def is None:
            raise NotFoundError(f"Filter '{filter_name}' not found in space")

        # Build the base query with space_id
        query: dict[str, Any] = {"space_id": space_id}

        # Add filter conditions
        for condition in filter_def.conditions:
            field_path = self._get_field_path(condition.field)
            mongo_operator = self._build_condition_query(condition.operator, condition.value)

            # Handle multiple conditions on the same field
            if field_path in query:
                # Combine with $and if there are multiple conditions on the same field
                if "$and" not in query:
                    existing_condition = {field_path: query.pop(field_path)}
                    query["$and"] = [existing_condition]
                query["$and"].append({field_path: mongo_operator})
            else:
                query[field_path] = mongo_operator

        return query

    def build_mongo_sort(self, space_id: UUID, filter_name: str) -> list[tuple[str, int]]:
        """Build MongoDB sort specification from a filter.

        Args:
            space_id: The space ID containing the filter
            filter_name: The name of the filter to use

        Returns:
            List of (field, direction) tuples for sorting

        Raises:
            NotFoundError: If space or filter not found
        """
        space = self.core.services.space.get_space(space_id)
        filter_def = space.get_filter(filter_name)
        if filter_def is None:
            raise NotFoundError(f"Filter '{filter_name}' not found in space")

        # Build sort specification
        if not filter_def.sort:
            # Default sort by number descending
            return [("number", -1)]

        sort_spec = []
        for field in filter_def.sort:
            if field.startswith("-"):
                # Descending sort
                field_name = field[1:]
                direction = -1
            else:
                # Ascending sort
                field_name = field
                direction = 1

            field_path = self._get_field_path(field_name)
            sort_spec.append((field_path, direction))

        return sort_spec

    def _get_field_path(self, field_name: str) -> str:
        """Get the MongoDB field path for a field name.

        System fields are used directly, custom fields are prefixed with 'fields.'
        """
        if field_name in NOTE_SYSTEM_FIELDS:
            # Special case for author field
            if field_name == "author":
                return "author_id"
            return field_name
        return f"fields.{field_name}"

    def _build_condition_query(self, operator: FilterOperator, value: Any) -> Any:  # noqa: ANN401
        """Build MongoDB query for a single condition.

        Args:
            operator: The filter operator
            value: The filter value

        Returns:
            MongoDB query value or operator document
        """
        # Handle null values
        if value is None:
            if operator == FilterOperator.EQ:
                return None
            if operator == FilterOperator.NE:
                return {"$ne": None}
            # This shouldn't happen due to validation, but handle it
            return None

        # Map operators to MongoDB
        if operator == FilterOperator.EQ:
            return value
        if operator == FilterOperator.NE:
            return {"$ne": value}
        if operator == FilterOperator.GT:
            return {"$gt": value}
        if operator == FilterOperator.GTE:
            return {"$gte": value}
        if operator == FilterOperator.LT:
            return {"$lt": value}
        if operator == FilterOperator.LTE:
            return {"$lte": value}
        if operator == FilterOperator.IN:
            return {"$in": value}
        if operator == FilterOperator.NIN:
            return {"$nin": value}
        if operator == FilterOperator.ALL:
            return {"$all": value}
        if operator == FilterOperator.CONTAINS:
            # Case-insensitive regex search
            return {"$regex": value, "$options": "i"}
        if operator == FilterOperator.STARTSWITH:
            # Anchor at start with case-insensitive
            return {"$regex": f"^{value}", "$options": "i"}
        if operator == FilterOperator.ENDSWITH:
            # Anchor at end with case-insensitive
            return {"$regex": f"{value}$", "$options": "i"}
        # Shouldn't happen, but default to equality
        return value
