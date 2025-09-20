"""Metadata endpoints for exposing system information."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.filter.models import FilterOperator, get_operators_for_field_type


class FieldTypeOperators(BaseModel):
    """Mapping of field type to available filter operators."""

    field_type: FieldType = Field(..., description="The field type")
    operators: list[FilterOperator] = Field(..., description="List of valid operators for this field type")


class FieldOperatorsResponse(BaseModel):
    """Response containing all field type operator mappings."""

    field_operators: list[FieldTypeOperators] = Field(..., description="List of field types and their valid operators")


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
async def get_field_operators() -> FieldOperatorsResponse:
    """Get valid operators for each field type."""
    field_operators = [
        FieldTypeOperators(field_type=field_type, operators=get_operators_for_field_type(field_type)) for field_type in FieldType
    ]
    return FieldOperatorsResponse(field_operators=field_operators)
