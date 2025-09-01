"""Session management models."""

from datetime import datetime
from typing import NewType
from uuid import UUID

from pydantic import Field

from spacenote.core.db import MongoModel
from spacenote.utils import now

AuthToken = NewType("AuthToken", str)


class Session(MongoModel):
    """User authentication session.

    Indexed on auth_token - unique, user_id, created_at (TTL 30 days).
    """

    user_id: UUID
    auth_token: str
    created_at: datetime = Field(default_factory=now)
