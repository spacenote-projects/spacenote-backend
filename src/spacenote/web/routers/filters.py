from fastapi import APIRouter

from spacenote.core.modules.filter.models import Filter
from spacenote.core.modules.space.models import Space
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["filters"])


@router.post(
    "/spaces/{space_slug}/filters",
    summary="Add filter to space",
    description="Add a new filter definition to an existing space. Only space members can add filters.",
    operation_id="addFilterToSpace",
    responses={
        200: {"description": "Filter added successfully"},
        400: {"model": ErrorResponse, "description": "Invalid filter data or filter name already exists"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def add_filter_to_space(space_slug: str, filter: Filter, app: AppDep, auth_token: AuthTokenDep) -> Space:
    return await app.add_filter_to_space(auth_token, space_slug, filter)


@router.delete(
    "/spaces/{space_slug}/filters/{filter_id}",
    summary="Remove filter from space",
    description="Remove a filter definition from a space. Only space members can remove filters.",
    operation_id="removeFilterFromSpace",
    status_code=204,
    responses={
        204: {"description": "Filter removed successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or filter not found"},
    },
)
async def remove_filter_from_space(space_slug: str, filter_id: str, app: AppDep, auth_token: AuthTokenDep) -> None:
    await app.remove_filter_from_space(auth_token, space_slug, filter_id)
