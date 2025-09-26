from fastapi import APIRouter
from pydantic import BaseModel, Field

from spacenote.core.modules.user.models import UserView
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["users"])


class CreateUserRequest(BaseModel):
    """Request to create a new user."""

    username: str = Field(..., min_length=1, description="Username for the new user")
    password: str = Field(..., min_length=1, description="Password for the new user")


@router.get(
    "/users",
    summary="List all users",
    description="Get all users in the system.",
    operation_id="listUsers",
    responses={
        200: {"description": "List of all users"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_users(app: AppDep, auth_token: AuthTokenDep) -> list[UserView]:
    return await app.get_all_users(auth_token)


@router.post(
    "/users",
    summary="Create new user",
    description="Create a new user account. Only accessible by admin users.",
    operation_id="createUser",
    responses={
        201: {"description": "User created successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Admin privileges required"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
    status_code=201,
)
async def create_user(create_data: CreateUserRequest, app: AppDep, auth_token: AuthTokenDep) -> UserView:
    return await app.create_user(auth_token, create_data.username, create_data.password)


@router.delete(
    "/users/{username}",
    summary="Delete user",
    description="Delete a user account. Only accessible by admin users. Cannot delete users who are members of any space.",
    operation_id="deleteUser",
    responses={
        204: {"description": "User deleted successfully"},
        400: {"model": ErrorResponse, "description": "Cannot delete user (in spaces or self-deletion)"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Admin privileges required"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
    status_code=204,
)
async def delete_user(username: str, app: AppDep, auth_token: AuthTokenDep) -> None:
    await app.delete_user(auth_token, username)
