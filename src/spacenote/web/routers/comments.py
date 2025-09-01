"""Comment-related API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from spacenote.core.modules.comment.models import Comment
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router: APIRouter = APIRouter(tags=["comments"])


class CreateCommentRequest(BaseModel):
    """Request to create a new comment."""

    content: str = Field(..., description="The comment text", min_length=1)


@router.get(
    "/spaces/{space_slug}/notes/{number}/comments",
    summary="List note comments",
    description="Get all comments for a specific note. Only space members can view comments.",
    operation_id="listComments",
    responses={
        200: {"description": "List of comments"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def list_comments(space_slug: str, number: int, app: AppDep, auth_token: AuthTokenDep) -> list[Comment]:
    return await app.get_note_comments(auth_token, space_slug, number)


@router.post(
    "/spaces/{space_slug}/notes/{number}/comments",
    summary="Create comment",
    description="Add a new comment to a note. Only space members can create comments.",
    operation_id="createComment",
    status_code=201,
    responses={
        201: {"description": "Comment created successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def create_comment(
    space_slug: str, number: int, request: CreateCommentRequest, app: AppDep, auth_token: AuthTokenDep
) -> Comment:
    return await app.create_comment(auth_token, space_slug, number, request.content)
