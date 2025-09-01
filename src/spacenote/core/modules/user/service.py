from typing import Any
from uuid import UUID

import bcrypt
import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.user.models import User
from spacenote.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class UserService(Service):
    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("users")
        self._users: dict[UUID, User] = {}

    def get_user(self, id: UUID) -> User:
        if id not in self._users:
            raise NotFoundError(f"User '{id}' not found")
        return self._users[id]

    def get_user_by_username(self, username: str) -> User:
        user = next((u for u in self._users.values() if u.username == username), None)
        if user is None:
            raise NotFoundError(f"User '{username}' not found")
        return user

    def has_user(self, id: UUID) -> bool:
        return id in self._users

    def has_username(self, username: str) -> bool:
        return any(user.username == username for user in self._users.values())

    def get_all_users(self) -> list[User]:
        """Get all users. Returns cached users list."""
        return list(self._users.values())

    async def create_user(self, username: str, password: str) -> User:
        if self.has_username(username):
            raise ValidationError(f"User '{username}' already exists")

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        res = await self._collection.insert_one(User(username=username, password_hash=password_hash).to_mongo())
        return await self.update_user_cache(res.inserted_id)

    def verify_password(self, username: str, password: str) -> bool:
        user = next((u for u in self._users.values() if u.username == username), None)
        if user is None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8"))

    async def ensure_admin_user_exists(self) -> None:
        if not self.has_username("admin"):
            await self.create_user("admin", "admin")

    async def update_all_users_cache(self) -> None:
        """Reload all users cache from database."""
        users = await User.list_cursor(self._collection.find())
        self._users = {user.id: user for user in users}

    async def update_user_cache(self, id: UUID) -> User:
        """Reload a specific user cache from database."""
        user = await self._collection.find_one({"_id": id})
        if user is None:
            raise NotFoundError(f"User '{id}' not found")
        self._users[id] = User.model_validate(user)
        return self._users[id]

    async def on_start(self) -> None:
        await self._collection.create_index([("username", 1)], unique=True)
        await self.update_all_users_cache()
        await self.ensure_admin_user_exists()
        logger.debug("user_service_started", user_count=len(self._users))
