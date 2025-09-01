from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel


class User(MongoModel):
    username: str
    password_hash: str  # bcrypt hash


class UserView(BaseModel):
    """User account information (API representation)."""

    username: str = Field(..., description="Username")

    @classmethod
    def from_domain(cls, user: User) -> "UserView":
        """Create view model from domain model."""
        return cls(username=user.username)
