from uuid import UUID

from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel


class User(MongoModel):
    """User domain model with credentials."""

    username: str
    password_hash: str  # bcrypt hash


class UserView(BaseModel):
    """User account information (API representation)."""

    id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")

    @classmethod
    def from_domain(cls, user: User) -> "UserView":
        """Create view model from domain model."""
        return cls(id=user.id, username=user.username)
