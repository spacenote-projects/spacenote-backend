"""Pure functions for building MongoDB queries from filters."""

from typing import Any
from uuid import UUID

from spacenote.core.modules.field.models import FieldType, FieldValueType, SpaceField, SpecialValue
from spacenote.core.modules.filter.models import FilterCondition, FilterOperator
from spacenote.core.modules.note.models import NOTE_SYSTEM_FIELDS
from spacenote.errors import ValidationError

# Mapping of filter operators to MongoDB query operators
_OPERATOR_MAPPING: dict[FilterOperator, str | None] = {
    FilterOperator.EQ: None,  # Direct value assignment
    FilterOperator.NE: "$ne",
    FilterOperator.GT: "$gt",
    FilterOperator.GTE: "$gte",
    FilterOperator.LT: "$lt",
    FilterOperator.LTE: "$lte",
    FilterOperator.IN: "$in",
    FilterOperator.NIN: "$nin",
    FilterOperator.ALL: "$all",
    FilterOperator.CONTAINS: "$regex",
    FilterOperator.STARTSWITH: "$regex",
    FilterOperator.ENDSWITH: "$regex",
}


def get_field_path(field_id: str) -> str:
    """Get the MongoDB field path for a field id.

    System fields are used directly, custom fields are prefixed with 'fields.'

    Args:
        field_id: The field identifier

    Returns:
        MongoDB field path
    """
    if field_id in NOTE_SYSTEM_FIELDS:
        return field_id
    return f"fields.{field_id}"


def build_condition_query(operator: FilterOperator, value: FieldValueType) -> dict[str, Any]:
    """Build MongoDB query for a single condition.

    Args:
        operator: The filter operator
        value: The filter value

    Returns:
        MongoDB query operator document
    """
    if value is None:
        if operator == FilterOperator.EQ:
            return {"$eq": None}
        if operator == FilterOperator.NE:
            return {"$ne": None}
        return {"$eq": None}

    if operator == FilterOperator.EQ:
        return {"$eq": value}

    mongo_op = _OPERATOR_MAPPING.get(operator)
    if mongo_op is None:
        raise ValueError(f"Operator {operator} not found in mapping - programming error")

    if operator == FilterOperator.CONTAINS:
        return {"$regex": value, "$options": "i"}
    if operator == FilterOperator.STARTSWITH:
        return {"$regex": f"^{value}", "$options": "i"}
    if operator == FilterOperator.ENDSWITH:
        return {"$regex": f"{value}$", "$options": "i"}

    return {mongo_op: value}


def build_mongo_sort(sort_fields: list[str]) -> list[tuple[str, int]]:
    """Build MongoDB sort specification from sort field list.

    Args:
        sort_fields: List of field IDs with optional '-' prefix for descending

    Returns:
        List of (field_path, direction) tuples for MongoDB sort
    """
    if not sort_fields:
        return [("number", -1)]

    sort_spec = []
    for field in sort_fields:
        if field.startswith("-"):
            field_id = field[1:]
            direction = -1
        else:
            field_id = field
            direction = 1

        field_path = get_field_path(field_id)
        sort_spec.append((field_path, direction))

    return sort_spec


def resolve_special_values(value: FieldValueType, field_type: FieldType, current_user_id: UUID | None) -> FieldValueType:
    """Resolve special values like $me to actual values.

    Args:
        value: The value to resolve
        field_type: The field type
        current_user_id: The current user ID for $me substitution

    Returns:
        Resolved value

    Raises:
        ValidationError: If special value cannot be resolved
    """
    if field_type == FieldType.USER and value == SpecialValue.ME:
        if current_user_id is None:
            raise ValidationError(f"Cannot use '{SpecialValue.ME}' without a logged-in user context")
        return current_user_id
    return value


def build_mongo_query(
    conditions: list[FilterCondition],
    field_definitions: dict[str, SpaceField],
    space_id: UUID,
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Build MongoDB query document from filter conditions.

    Args:
        conditions: List of filter conditions
        field_definitions: Map of field ID to field definition
        space_id: The space ID to filter by
        current_user_id: The current user ID for special value substitution

    Returns:
        MongoDB query document

    Raises:
        ValidationError: If special values cannot be resolved
    """
    query: dict[str, Any] = {"space_id": space_id}

    for condition in conditions:
        field_path = get_field_path(condition.field)
        field = field_definitions[condition.field]

        value = resolve_special_values(condition.value, field.type, current_user_id)
        mongo_operator = build_condition_query(condition.operator, value)

        if field_path in query:
            if "$and" not in query:
                existing_condition = {field_path: query.pop(field_path)}
                query["$and"] = [existing_condition]
            query["$and"].append({field_path: mongo_operator})
        else:
            query[field_path] = mongo_operator

    return query
