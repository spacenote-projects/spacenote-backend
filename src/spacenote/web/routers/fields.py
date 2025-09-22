from fastapi import APIRouter

from spacenote.core.modules.field.models import SpaceField
from spacenote.core.modules.space.models import Space
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["fields"])


@router.post(
    "/spaces/{space_slug}/fields",
    summary="Add field to space",
    description="Add a new field definition to an existing space. Only space members can add fields.",
    operation_id="addFieldToSpace",
    responses={
        200: {"description": "Field added successfully"},
        400: {"model": ErrorResponse, "description": "Invalid field data or field name already exists"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def add_field_to_space(space_slug: str, field: SpaceField, app: AppDep, auth_token: AuthTokenDep) -> Space:
    return await app.add_field_to_space(auth_token, space_slug, field)


@router.delete(
    "/spaces/{space_slug}/fields/{field_id}",
    summary="Remove field from space",
    description=(
        "Remove a field definition from a space. Only space members can remove fields. The field must not be in use by any notes."
    ),
    operation_id="removeFieldFromSpace",
    status_code=204,
    responses={
        204: {"description": "Field removed successfully"},
        400: {"model": ErrorResponse, "description": "Field is in use and cannot be removed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or field not found"},
    },
)
async def remove_field_from_space(space_slug: str, field_id: str, app: AppDep, auth_token: AuthTokenDep) -> None:
    await app.remove_field_from_space(auth_token, space_slug, field_id)
