"""Metadata endpoints for exposing system information."""

from importlib.metadata import version
from typing import Annotated

from fastapi import APIRouter, Depends

from spacenote.config import Config
from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.filter.models import FIELD_TYPE_OPERATORS, FilterOperator
from spacenote.web.deps import get_config

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


@router.get(
    "/api/v1/metadata/version",
    summary="Get version information",
    description="Returns build and version information including package version, git commit hash, commit date, and build time.",
    operation_id="getVersion",
)
async def get_version(config: Annotated[Config, Depends(get_config)]) -> dict[str, str]:
    """Get version information."""
    return {
        "version": version("spacenote"),
        "git_commit_hash": config.git_commit_hash,
        "git_commit_date": config.git_commit_date,
        "build_time": config.build_time,
    }
