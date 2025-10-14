from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    """Authentication request."""

    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")


class LoginResponse(BaseModel):
    """Authentication response."""

    token: str = Field(..., description="Authentication token for subsequent requests")


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

    token = await app.login(login_data.username, login_data.password)

    # Set cookie for browser-based clients
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=30 * 24 * 60 * 60,  # 30 days to match session TTL
    )

    return LoginResponse(token=token)


@router.post(
    "/auth/logout",
    summary="End session",
    description="Invalidate the current authentication session.",
    operation_id="logout",
    status_code=204,
    responses={
        204: {"description": "Successfully logged out"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def logout(app: AppDep, auth_token: AuthTokenDep, response: Response) -> None:
    await app.logout(auth_token)
    response.delete_cookie("token")
