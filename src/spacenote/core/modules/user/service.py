from types import MappingProxyType
from typing import Any
from uuid import UUID

import bcrypt
import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.user.models import User
from spacenote.core.modules.user.validators import validate_password
from spacenote.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class UserService(Service):
    """Manages users with in-memory cache."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("users")
        self._users: dict[UUID, User] = {}

    def get_user(self, user_id: UUID) -> User:
        """Get user by ID from cache."""
        if user_id not in self._users:
            raise NotFoundError(f"User '{user_id}' not found")
        return self._users[user_id]

    def get_user_by_username(self, username: str) -> User:
        """Get user by username from cache."""
        user = next((u for u in self._users.values() if u.username == username), None)
        if user is None:
            raise NotFoundError(f"User '{username}' not found")
        return user

    def has_user(self, user_id: UUID) -> bool:
        """Check if user exists by ID."""
        return user_id in self._users

    def has_username(self, username: str) -> bool:
        """Check if username exists."""
        return any(user.username == username for user in self._users.values())

    def get_all_users(self) -> list[User]:
        """Get all users from cache."""
        return list(self._users.values())

    def get_user_cache(self) -> MappingProxyType[UUID, User]:
        """Get read-only view of user cache for formatting purposes."""
        return MappingProxyType(self._users)

    async def create_user(self, username: str, password: str) -> User:
        """Create user with hashed password."""
        if self.has_username(username):
            raise ValidationError(f"User '{username}' already exists")

        validate_password(password)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        res = await self._collection.insert_one(User(username=username, password_hash=password_hash).to_mongo())
        return await self.update_user_cache(res.inserted_id)

    def verify_password(self, username: str, password: str) -> bool:
        """Verify password against stored hash."""
        user = next((u for u in self._users.values() if u.username == username), None)
        if user is None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8"))

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        """Change user password after verifying current password."""
        user = self.get_user(user_id)
        if not bcrypt.checkpw(old_password.encode("utf-8"), user.password_hash.encode("utf-8")):
            raise ValidationError("Invalid current password")

        validate_password(new_password)
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await self._collection.update_one({"_id": user_id}, {"$set": {"password_hash": password_hash}})
        await self.update_user_cache(user_id)

    async def delete_user(self, user_id: UUID) -> None:
        """Delete a user from the system."""
        if not self.has_user(user_id):
            raise NotFoundError(f"User '{user_id}' not found")

        if self.core.services.space.is_user_member_of_any_space(user_id):
            raise ValidationError("Cannot delete user: member of one or more spaces")

        await self._collection.delete_one({"_id": user_id})
        del self._users[user_id]

    async def ensure_admin_user_exists(self) -> None:
        """Create default admin user if not exists."""
        if not self.has_username("admin"):
            await self.create_user("admin", "admin")

    async def update_all_users_cache(self) -> None:
        """Reload all users cache from database."""
        users = await User.list_cursor(self._collection.find())
        self._users = {user.id: user for user in users}

    async def update_user_cache(self, user_id: UUID) -> User:
        """Reload a specific user cache from database."""
        user = await self._collection.find_one({"_id": user_id})
        if user is None:
            raise NotFoundError(f"User '{user_id}' not found")
        self._users[user_id] = User.model_validate(user)
        return self._users[user_id]

    async def on_start(self) -> None:
        """Initialize indexes, cache, and admin user."""
        await self._collection.create_index([("username", 1)], unique=True)
        await self.update_all_users_cache()
        await self.ensure_admin_user_exists()
        logger.debug("user_service_started", user_count=len(self._users))
