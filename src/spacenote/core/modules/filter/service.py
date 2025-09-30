from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldType, SpaceField, SpecialValue
from spacenote.core.modules.filter.models import FIELD_TYPE_OPERATORS, Filter, FilterOperator
from spacenote.core.modules.filter.validators import validate_filter_value
from spacenote.core.modules.note.models import NOTE_SYSTEM_FIELDS
from spacenote.errors import NotFoundError, ValidationError


class FilterService(Service):
    """Service for filter validation and management."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    def _get_system_field_definition(self, field_id: str) -> SpaceField | None:
        """Get virtual field definition for system fields."""
        if field_id == "number":
            return SpaceField(id="number", type=FieldType.INT, required=True)
        if field_id == "created_at":
            return SpaceField(id="created_at", type=FieldType.DATETIME, required=True)
        if field_id == "user_id":
            return SpaceField(id="user_id", type=FieldType.USER, required=True)
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

        # Build the base query with space_id
        query: dict[str, Any] = {"space_id": space_id}

        # Add filter conditions
        for condition in filter_def.conditions:
            field_path = self._get_field_path(condition.field)

            # Get field definition to check if it's a USER field
            field = space.get_field(condition.field)
            if field is None:
                field = self._get_system_field_definition(condition.field)

            # Replace $me with current user ID for USER fields
            value = condition.value
            if field and field.type == FieldType.USER and value == SpecialValue.ME:
                if current_user_id is None:
                    raise ValidationError(f"Cannot use '{SpecialValue.ME}' without a logged-in user context")
                value = current_user_id

            mongo_operator = self._build_condition_query(condition.operator, value)

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

        # Build sort specification
        if not filter_def.sort:
            # Default sort by number descending
            return [("number", -1)]

        sort_spec = []
        for field in filter_def.sort:
            if field.startswith("-"):
                # Descending sort
                field_id = field[1:]
                direction = -1
            else:
                # Ascending sort
                field_id = field
                direction = 1

            field_path = self._get_field_path(field_id)
            sort_spec.append((field_path, direction))

        return sort_spec

    def _get_field_path(self, field_id: str) -> str:
        """Get the MongoDB field path for a field id.

        System fields are used directly, custom fields are prefixed with 'fields.'
        """
        if field_id in NOTE_SYSTEM_FIELDS:
            return field_id
        return f"fields.{field_id}"

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
