"""Metadata endpoints for exposing system information."""

from fastapi import APIRouter

from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.filter.models import FIELD_TYPE_OPERATORS, FilterOperator

router = APIRouter(tags=["metadata"])


@router.get(
    "/api/v1/metadata/field-operators",
    summary="Get valid operators for each field type",
    description=(
        "Returns a mapping of field types to their valid filter operators. "
        "This information can be used by the frontend to dynamically show/hide operators based on the selected field type."
    ),
    operation_id="getFieldOperators",
)
async def get_field_operators() -> dict[FieldType, list[FilterOperator]]:
    """Get valid operators for each field type."""
    return {field_type: list(operators) for field_type, operators in FIELD_TYPE_OPERATORS.items()}
