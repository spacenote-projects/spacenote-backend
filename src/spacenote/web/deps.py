from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

from spacenote.app import App
from spacenote.core.modules.session.models import AuthToken
from spacenote.errors import AuthenticationError

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name="auth_token", auto_error=False)


async def get_app(request: Request) -> App:
    return cast(App, request.app.state.app)


async def get_auth_token(
    app: Annotated[App, Depends(get_app)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    token_cookie: Annotated[str | None, Depends(cookie_scheme)] = None,
) -> AuthToken:
    """Get and validate auth token from Authorization Bearer header or cookie."""

    # Check Bearer token first (preferred)
    if credentials and credentials.scheme == "Bearer":
        auth_token = AuthToken(credentials.credentials)
        if await app.is_auth_token_valid(auth_token):
            return auth_token

    # Fallback to cookie
    if token_cookie:
        auth_token = AuthToken(token_cookie)
        if await app.is_auth_token_valid(auth_token):
            return auth_token

    raise AuthenticationError


# Type aliases for dependencies
AppDep = Annotated[App, Depends(get_app)]
AuthTokenDep = Annotated[AuthToken, Depends(get_auth_token)]
