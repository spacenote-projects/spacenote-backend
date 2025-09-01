from uuid import UUID

from spacenote.core.core import Service
from spacenote.core.modules.session.models import AuthToken
from spacenote.core.modules.user.models import User
from spacenote.errors import AccessDeniedError


class AccessService(Service):
    async def ensure_authenticated(self, auth_token: AuthToken) -> User:
        """Ensure the user is authenticated."""
        return await self.core.services.session.get_authenticated_user(auth_token)

    async def ensure_space_member(self, auth_token: AuthToken, space_id: UUID) -> None:
        """Ensure the authenticated user is a member of the specified space."""
        user = await self.core.services.session.get_authenticated_user(auth_token)
        space = self.core.services.space.get_space(space_id)
        if user.id not in space.members:
            raise AccessDeniedError(f"Access denied: user '{user.id}' is not a member of space '{space_id}'")

    async def ensure_admin(self, auth_token: AuthToken) -> None:
        """Ensure the authenticated user is admin, raise AccessDeniedError if not."""
        user = await self.core.services.session.get_authenticated_user(auth_token)
        if user.username != "admin":
            raise AccessDeniedError("Admin privileges required")
