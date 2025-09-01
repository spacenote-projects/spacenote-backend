import secrets
from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.session.models import AuthToken, Session
from spacenote.core.modules.user.models import User
from spacenote.errors import AuthenticationError


class SessionService(Service):
    """Service for managing user sessions."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("sessions")
        self._authenticated_users: dict[AuthToken, User] = {}

    async def on_start(self) -> None:
        """Create indexes on startup."""
        # Unique index for auth_token (for authentication lookups)
        await self._collection.create_index([("auth_token", 1)], unique=True)
        # Single index for user_id (for finding sessions by user)
        await self._collection.create_index([("user_id", 1)])
        # TTL index for automatic session cleanup (30 days expiry)
        await self._collection.create_index([("created_at", 1)], expireAfterSeconds=30 * 24 * 60 * 60)

    async def create_session(self, user_id: UUID) -> AuthToken:
        auth_token = AuthToken(secrets.token_urlsafe(32))
        new_session = Session(user_id=user_id, auth_token=auth_token)
        await self._collection.insert_one(new_session.to_mongo())
        return auth_token

    async def get_authenticated_user(self, auth_token: AuthToken) -> User:
        # Check cache first
        if auth_token in self._authenticated_users:
            return self._authenticated_users[auth_token]

        # Get session from database
        session = await self._collection.find_one({"auth_token": auth_token})
        if session is None:
            raise AuthenticationError("Invalid or expired session")

        if not self.core.services.user.has_user(session["user_id"]):
            raise AuthenticationError("Invalid or expired session")

        user = self.core.services.user.get_user(session["user_id"])
        self._authenticated_users[auth_token] = user
        return user

    async def is_auth_token_valid(self, auth_token: AuthToken) -> bool:
        try:
            await self.get_authenticated_user(auth_token)
        except AuthenticationError:
            return False
        return True

    async def invalidate_session(self, auth_token: AuthToken) -> None:
        """Invalidate a session by removing it from the database."""
        if auth_token in self._authenticated_users:
            del self._authenticated_users[auth_token]
        await self._collection.delete_one({"auth_token": auth_token})
