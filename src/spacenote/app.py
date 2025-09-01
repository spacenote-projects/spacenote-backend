from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from spacenote.config import Config
from spacenote.core.core import Core
from spacenote.core.modules.session.models import AuthToken
from spacenote.core.modules.user.models import User
from spacenote.errors import AuthenticationError


class App:
    def __init__(self, config: Config) -> None:
        self._core = Core(config)

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None]:
        """Application lifespan management - delegates to Core."""
        async with self._core.lifespan():
            yield

    async def is_auth_token_valid(self, auth_token: AuthToken) -> bool:
        return await self._core.services.session.is_auth_token_valid(auth_token)

    async def login(self, username: str, password: str) -> AuthToken:
        if not self._core.services.user.verify_password(username, password):
            raise AuthenticationError
        user = self._resolve_user(username)
        return await self._core.services.session.create_session(user.id)

    async def logout(self, auth_token: AuthToken) -> None:
        await self._core.services.access.ensure_authenticated(auth_token)
        await self._core.services.session.invalidate_session(auth_token)

    # === Private resolver methods ===
    def _resolve_user(self, username: str) -> User:
        """Resolve username to User object. Raises NotFoundError if not found."""
        return self._core.services.user.get_user_by_username(username)
