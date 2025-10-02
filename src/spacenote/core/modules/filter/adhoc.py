"""Ad-hoc query parser for dynamic filtering."""

import contextlib
import json
import urllib.parse
from typing import Any

from spacenote.core.modules.filter.models import (
    FIELD_TYPE_OPERATORS,
    SYSTEM_FIELD_DEFINITIONS,
    FilterCondition,
    FilterOperator,
)
from spacenote.core.modules.filter.validators import validate_filter_value
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User
from spacenote.errors import ValidationError


def parse_adhoc_query(query: str, space: Space, members: list[User]) -> list[FilterCondition]:
    """Parse ad-hoc query string into filter conditions.

    Query format: field:operator:value,field:operator:value
    - Conditions are separated by commas
    - Each condition has format: field:operator:value
    - For array operators (in, nin, all), value should be JSON array: tags:in:["value1","value2"]
    - Simple values should be URL-encoded if they contain special characters

    Args:
        query: Query string to parse
        space: The space to validate fields against
        members: List of space members for user field validation

    Returns:
        List of validated FilterCondition objects

    Raises:
        ValidationError: If query syntax is invalid or validation fails

    Examples:
        status:eq:active
        status:eq:active,priority:gte:5
        tags:in:["shopping","groceries"]
        user_id:eq:$me,created_at:gte:2024-01-01
    """
    if not query or not query.strip():
        return []

    conditions: list[FilterCondition] = []
    condition_strings = query.split(",")

    for cond_str in condition_strings:
        condition_str = cond_str.strip()
        if not condition_str:
            continue

        # Split by ':' with maxsplit=2 to handle values containing ':'
        parts = condition_str.split(":", 2)
        if len(parts) != 3:
            raise ValidationError(f"Invalid query syntax at condition: '{condition_str}'. Expected format: field:operator:value")

        field_id, operator_str, value_raw = parts

        # Validate field exists
        field = space.get_field(field_id)
        if field is None:
            field = SYSTEM_FIELD_DEFINITIONS().get(field_id)
            if field is None:
                raise ValidationError(f"Field '{field_id}' not found in space")

        # Parse operator
        try:
            operator = FilterOperator(operator_str)
        except ValueError as e:
            raise ValidationError(f"Unknown operator '{operator_str}'") from e

        # Validate operator is compatible with field type
        valid_operators = FIELD_TYPE_OPERATORS.get(field.type)
        if valid_operators is None:
            raise ValidationError(f"Unknown field type: {field.type}")
        if operator not in valid_operators:
            raise ValidationError(f"Operator '{operator}' is not valid for field '{field_id}' of type '{field.type}'")

        # Parse value based on operator type
        value: Any
        if operator in (FilterOperator.IN, FilterOperator.NIN, FilterOperator.ALL):
            # Array operators - expect JSON array
            try:
                decoded_value = urllib.parse.unquote(value_raw)
                value = json.loads(decoded_value)
                if not isinstance(value, list):
                    raise ValidationError(f"Operator '{operator}' expects a JSON array value, got: {type(value).__name__}")
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON array for operator '{operator}': {value_raw}") from e
        else:
            # Simple value - URL decode
            value = urllib.parse.unquote(value_raw)

            # Try to parse as JSON for null, bool, number
            if value.lower() == "null":
                value = None
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                # Try to parse as number
                with contextlib.suppress(ValueError):
                    value = float(value) if "." in value else int(value)

        # Validate and normalize value
        normalized_value = validate_filter_value(field, operator, value, space, members)

        # Create condition
        condition = FilterCondition(field=field_id, operator=operator, value=normalized_value)
        conditions.append(condition)

    return conditions
