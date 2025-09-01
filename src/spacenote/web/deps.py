from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import APIKeyCookie, APIKeyHeader

from spacenote.app import App
from spacenote.core.modules.session.models import AuthToken
from spacenote.errors import AuthenticationError

# Security schemes
header_scheme = APIKeyHeader(name="X-Auth-Token", auto_error=False)
cookie_scheme = APIKeyCookie(name="auth_token", auto_error=False)


async def get_app(request: Request) -> App:
    return cast(App, request.app.state.app)


async def get_auth_token(
    app: Annotated[App, Depends(get_app)],
    token_header: Annotated[str | None, Depends(header_scheme)] = None,
    token_cookie: Annotated[str | None, Depends(cookie_scheme)] = None,
) -> AuthToken:
    """Get and validate auth token from header or cookie."""

    # Check header first
    if token_header:
        auth_token = AuthToken(token_header)
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
