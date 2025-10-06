"""Comment-related API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from spacenote.core.modules.comment.models import Comment
from spacenote.core.pagination import PaginationResult
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router: APIRouter = APIRouter(tags=["comments"])


class CreateCommentRequest(BaseModel):
    """Request to create a new comment."""

    content: str = Field(..., description="The comment text", min_length=1)
    raw_fields: dict[str, str] | None = Field(
        None, description="Optional field updates (must be in space.comment_editable_fields)"
    )


@router.get(
    "/spaces/{space_slug}/notes/{number}/comments",
    summary="List note comments",
    description="Get paginated comments for a specific note. Only space members can view comments.",
    operation_id="listComments",
    responses={
        200: {"description": "Paginated list of comments"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def list_comments(
    space_slug: str,
    number: int,
    app: AppDep,
    auth_token: AuthTokenDep,
    limit: Annotated[int, Query(ge=1, description="Maximum items to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> PaginationResult[Comment]:
    return await app.get_note_comments(auth_token, space_slug, number, limit, offset)


@router.post(
    "/spaces/{space_slug}/notes/{number}/comments",
    summary="Create comment",
    description=(
        "Add a new comment to a note. Optionally update note fields if configured in "
        "space.comment_editable_fields. Only space members can create comments."
    ),
    operation_id="createComment",
    status_code=201,
    responses={
        201: {"description": "Comment created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid field data or field not in comment_editable_fields"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def create_comment(
    space_slug: str, number: int, request: CreateCommentRequest, app: AppDep, auth_token: AuthTokenDep
) -> Comment:
    return await app.create_comment(auth_token, space_slug, number, request.content, request.raw_fields)
