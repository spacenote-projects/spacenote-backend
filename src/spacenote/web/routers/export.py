"""Export/import API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from spacenote.core.modules.export.models import ExportData
from spacenote.core.modules.space.models import Space
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["export"])


@router.get(
    "/spaces/{space_slug}/export",
    summary="Export space configuration",
    description="Export a space configuration as portable JSON. Only space members can export. "
    "Optionally include all notes and comments data.",
    operation_id="exportSpace",
    responses={
        200: {"description": "Space exported successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def export_space(
    space_slug: str,
    app: AppDep,
    auth_token: AuthTokenDep,
    include_data: Annotated[bool, Query(description="Include notes and comments data in export")] = False,
) -> ExportData:
    return await app.export_space(auth_token, space_slug, include_data)


@router.post(
    "/spaces/import",
    summary="Import space configuration",
    description="Import a space configuration from exported JSON. Optionally rename the space with new_slug.",
    operation_id="importSpace",
    status_code=201,
    responses={
        201: {"description": "Space imported successfully"},
        400: {"model": ErrorResponse, "description": "Invalid data or slug already exists"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def import_space(
    export_data: ExportData,
    app: AppDep,
    auth_token: AuthTokenDep,
    new_slug: Annotated[str | None, Query(description="Optional new slug to rename the space on import")] = None,
) -> Space:
    return await app.import_space(auth_token, export_data, new_slug)
