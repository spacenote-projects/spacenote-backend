from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from spacenote.web.deps import AppDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    """Authentication request."""

    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")


class LoginResponse(BaseModel):
    """Authentication response."""

    auth_token: str = Field(..., description="Authentication token for subsequent requests")


@router.post(
    "/auth/login",
    summary="Authenticate user",
    description="Authenticate with username and password to receive an authentication token.",
    operation_id="login",
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
    },
)
async def login(login_data: LoginRequest, app: AppDep, response: Response) -> LoginResponse:
    """Authenticate user and create session."""

    auth_token = await app.login(login_data.username, login_data.password)

    # Set cookie for browser-based testing
    response.set_cookie(
        key="auth_token",
        value=auth_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    return LoginResponse(auth_token=auth_token)


# @router.post(
#     "/auth/logout",
#     summary="End session",
#     description="Invalidate the current authentication session.",
#     operation_id="logout",
#     responses={
#         200: {"description": "Successfully logged out"},
#         401: {"model": ErrorResponse, "description": "Not authenticated"},
#     },
# )
# async def logout(app: AppDep, auth_token: AuthTokenDep, response: Response) -> dict[str, str]:
#     """Logout and invalidate session."""
#     await app.logout(auth_token)
#     response.delete_cookie("auth_token")
#     return {"message": "Logged out successfully"}
