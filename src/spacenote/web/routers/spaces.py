from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from spacenote.core.modules.space.models import Space
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["spaces"])


class CreateSpaceRequest(BaseModel):
    """Request to create a new space."""

    slug: str = Field(
        ...,
        description="URL-friendly unique identifier (lowercase letters, numbers, hyphens; no leading/trailing/double hyphens)",
        pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    title: str = Field(..., description="Human-readable space name")
    description: str = Field(..., description="Space description")

    model_config = {
        "json_schema_extra": {
            "examples": [{"slug": "my-tasks", "title": "My Task Tracker", "description": "Track personal tasks and projects"}]
        }
    }


@router.get(
    "/spaces",
    summary="List user spaces",
    description="Get all spaces where the authenticated user is a member.",
    operation_id="listSpaces",
    responses={
        200: {"description": "List of spaces"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_spaces(app: AppDep, auth_token: AuthTokenDep) -> list[Space]:
    return await app.get_spaces_by_member(auth_token)


@router.post(
    "/spaces",
    summary="Create new space",
    description="Create a new space with the specified slug and title. The authenticated user becomes a member.",
    operation_id="createSpace",
    status_code=201,
    responses={
        201: {"description": "Space created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data or slug already exists"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def create_space(req: CreateSpaceRequest, app: AppDep, auth_token: AuthTokenDep) -> Space:
    return await app.create_space(auth_token, req.slug, req.title, req.description)


class AddMemberRequest(BaseModel):
    """Request to add a member to a space."""

    username: str = Field(..., description="Username of the user to add as a member")


@router.post(
    "/spaces/{space_slug}/members",
    summary="Add member to space",
    description="Add a new member to a space. Only existing space members can add new members.",
    operation_id="addMemberToSpace",
    responses={
        200: {"description": "Member added successfully"},
        400: {"model": ErrorResponse, "description": "User is already a member"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or user not found"},
    },
)
async def add_member_to_space(space_slug: str, req: AddMemberRequest, app: AppDep, auth_token: AuthTokenDep) -> Space:
    return await app.add_space_member(auth_token, space_slug, req.username)


@router.delete(
    "/spaces/{space_slug}/members/{username}",
    summary="Remove member from space",
    description=(
        "Remove a member from a space. Only existing space members can remove other members. Cannot remove the last member."
    ),
    operation_id="removeMemberFromSpace",
    status_code=204,
    responses={
        204: {"description": "Member removed successfully"},
        400: {"model": ErrorResponse, "description": "Cannot remove last member or user is not a member"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or user not found"},
    },
)
async def remove_member_from_space(space_slug: str, username: str, app: AppDep, auth_token: AuthTokenDep) -> None:
    await app.remove_space_member(auth_token, space_slug, username)


class UpdateSpaceTemplateRequest(BaseModel):
    """Request to update a space template."""

    name: Literal["note_detail", "note_list"] = Field(..., description="Template name to update")
    content: str | None = Field(..., description="Template content (Liquid template) or null to clear")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "note_detail",
                    "content": "# {{ note.title }}\n\n{{ note.description }}",
                }
            ]
        }
    }


@router.patch(
    "/spaces/{space_slug}/templates",
    summary="Update space template",
    description="Update a specific template for a space. Only space members can update templates.",
    operation_id="updateSpaceTemplate",
    responses={
        200: {"description": "Template updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid template name"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def update_space_template(space_slug: str, req: UpdateSpaceTemplateRequest, app: AppDep, auth_token: AuthTokenDep) -> Space:
    return await app.update_space_template(auth_token, space_slug, req.name, req.content)


@router.delete(
    "/spaces/{space_slug}",
    summary="Delete space",
    description="Delete a space and all its data including notes and comments. Only admins can delete spaces.",
    operation_id="deleteSpace",
    status_code=204,
    responses={
        204: {"description": "Space deleted successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Admin privileges required"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def delete_space(space_slug: str, app: AppDep, auth_token: AuthTokenDep) -> None:
    await app.delete_space(auth_token, space_slug)
