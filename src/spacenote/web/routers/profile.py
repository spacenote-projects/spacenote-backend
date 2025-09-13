from fastapi import APIRouter
from pydantic import BaseModel, Field

from spacenote.core.modules.user.models import UserView
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["profile"])


class ChangePasswordRequest(BaseModel):
    """Request to change user password."""

    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=1, description="New password")


@router.get(
    "/profile",
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user.",
    operation_id="getCurrentUserProfile",
    responses={
        200: {"description": "Current user profile"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_profile(app: AppDep, auth_token: AuthTokenDep) -> UserView:
    return await app.get_current_user(auth_token)


@router.post(
    "/profile/change-password",
    summary="Change password",
    description="Change the password for the currently authenticated user.",
    operation_id="changePassword",
    status_code=204,
    responses={
        204: {"description": "Password changed successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated or invalid current password"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
async def change_password(request: ChangePasswordRequest, app: AppDep, auth_token: AuthTokenDep) -> None:
    await app.change_password(auth_token, request.old_password, request.new_password)
