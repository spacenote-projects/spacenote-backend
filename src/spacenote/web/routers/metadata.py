"""Metadata endpoints for exposing system information."""

from fastapi import APIRouter

from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.filter.models import FilterOperator
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["metadata"])


@router.get(
    "/metadata/field-operators",
    summary="Get valid operators for each field type",
    description=(
        "Returns a mapping of field types to their valid filter operators. "
        "This information can be used by the frontend to dynamically show/hide operators based on the selected field type."
    ),
    operation_id="getFieldOperators",
    responses={
        200: {"description": "Mapping of field types to valid operators"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_field_operators(app: AppDep, auth_token: AuthTokenDep) -> dict[FieldType, list[FilterOperator]]:
    """Get valid operators for each field type."""
    return await app.get_field_operators(auth_token)


@router.get(
    "/metadata/version",
    summary="Get version information",
    description="Returns build and version information including package version, git commit hash, commit date, and build time.",
    operation_id="getVersion",
    responses={
        200: {"description": "Version and build information"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_version(app: AppDep, auth_token: AuthTokenDep) -> dict[str, str]:
    """Get version information."""
    return await app.get_version(auth_token)
