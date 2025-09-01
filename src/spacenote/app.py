from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from spacenote.config import Config
from spacenote.core.core import Core
from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.field.models import SpaceField
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.session.models import AuthToken
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User, UserView
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

    async def get_all_users(self, auth_token: AuthToken) -> list[UserView]:
        """Get all users."""
        await self._core.services.access.ensure_authenticated(auth_token)
        users = self._core.services.user.get_all_users()
        return [UserView.from_domain(user) for user in users]

    async def create_user(self, auth_token: AuthToken, username: str, password: str) -> UserView:
        """Create a new user."""
        await self._core.services.access.ensure_admin(auth_token)
        user = await self._core.services.user.create_user(username, password)
        return UserView.from_domain(user)

    async def get_spaces_by_member(self, auth_token: AuthToken) -> list[Space]:
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return self._core.services.space.get_spaces_by_member(current_user.id)

    async def create_space(self, auth_token: AuthToken, slug: str, title: str) -> Space:
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.space.create_space(slug, title, current_user.id)

    async def add_field_to_space(self, auth_token: AuthToken, space_slug: str, field: SpaceField) -> Space:
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.add_field(space.id, field)

    async def get_notes_by_space(self, auth_token: AuthToken, space_slug: str) -> list[Note]:
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.note.list_notes(space.id)

    async def get_note_by_number(self, auth_token: AuthToken, space_slug: str, number: int) -> Note:
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.note.get_note_by_number(space.id, number)

    async def create_note(self, auth_token: AuthToken, space_slug: str, raw_fields: dict[str, str]) -> Note:
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.note.create_note(space.id, current_user.id, raw_fields)

    async def get_note_comments(self, auth_token: AuthToken, space_slug: str, note_number: int) -> list[Comment]:
        space, note = await self._resolve_note(space_slug, note_number)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.comment.get_note_comments(note.id)

    async def create_comment(self, auth_token: AuthToken, space_slug: str, note_number: int, content: str) -> Comment:
        space, note = await self._resolve_note(space_slug, note_number)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        current_user = await self._core.services.session.get_authenticated_user(auth_token)
        return await self._core.services.comment.create_comment(note.id, space.id, current_user.id, content)

    # === Private resolver methods ===
    def _resolve_space(self, slug: str) -> Space:
        """Resolve space slug to Space object. Raises NotFoundError if not found."""
        return self._core.services.space.get_space_by_slug(slug)

    def _resolve_user(self, username: str) -> User:
        """Resolve username to User object. Raises NotFoundError if not found."""
        return self._core.services.user.get_user_by_username(username)

    async def _resolve_note(self, space_slug: str, number: int) -> tuple[Space, Note]:
        """Resolve space slug and note number to Space and Note objects."""
        space = self._resolve_space(space_slug)
        note = await self._core.services.note.get_note_by_number(space.id, number)
        return space, note
