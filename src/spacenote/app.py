from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from spacenote.config import Config
from spacenote.core.core import Core
from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.export.models import ExportData
from spacenote.core.modules.field.models import SpaceField
from spacenote.core.modules.filter.models import Filter
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.session.models import AuthToken
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.telegram.models import TelegramEventType, TelegramIntegration, TelegramNotificationConfig
from spacenote.core.modules.user.models import User, UserView
from spacenote.core.pagination import PaginationResult
from spacenote.errors import AuthenticationError, ValidationError


class App:
    """Facade for all application operations, validates permissions before delegating to Core."""

    def __init__(self, config: Config) -> None:
        self._core = Core(config)

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None]:
        """Application lifespan management - delegates to Core."""
        async with self._core.lifespan():
            yield

    async def is_auth_token_valid(self, auth_token: AuthToken) -> bool:
        """Check if authentication token is valid."""
        return await self._core.services.session.is_auth_token_valid(auth_token)

    async def login(self, username: str, password: str) -> AuthToken:
        """Authenticate user and create session."""
        if not self._core.services.user.verify_password(username, password):
            raise AuthenticationError
        user = self._resolve_user(username)
        return await self._core.services.session.create_session(user.id)

    async def logout(self, auth_token: AuthToken) -> None:
        """Invalidate user session."""
        await self._core.services.access.ensure_authenticated(auth_token)
        await self._core.services.session.invalidate_session(auth_token)

    async def get_all_users(self, auth_token: AuthToken) -> list[UserView]:
        """Get all users (requires authentication)."""
        await self._core.services.access.ensure_authenticated(auth_token)
        users = self._core.services.user.get_all_users()
        return [UserView.from_domain(user) for user in users]

    async def create_user(self, auth_token: AuthToken, username: str, password: str) -> UserView:
        """Create a new user (admin only)."""
        await self._core.services.access.ensure_admin(auth_token)
        user = await self._core.services.user.create_user(username, password)
        return UserView.from_domain(user)

    async def delete_user(self, auth_token: AuthToken, username: str) -> None:
        """Delete a user (admin only, cannot delete self or users in spaces)."""
        current_user = await self._core.services.access.ensure_admin(auth_token)
        user = self._resolve_user(username)

        if user.id == current_user.id:
            raise ValidationError("Cannot delete yourself")

        await self._core.services.user.delete_user(user.id)

    async def get_spaces_by_member(self, auth_token: AuthToken) -> list[Space]:
        """Get spaces where current user is a member."""
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return self._core.services.space.get_spaces_by_member(current_user.id)

    async def create_space(self, auth_token: AuthToken, slug: str, title: str, description: str) -> Space:
        """Create new space with current user as owner."""
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.space.create_space(slug, title, description, current_user.id)

    async def add_field_to_space(self, auth_token: AuthToken, space_slug: str, field: SpaceField) -> Space:
        """Add custom field to space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        await self._core.services.field.add_field_to_space(space.id, field)
        return self._resolve_space(space_slug)

    async def get_notes_by_space(
        self,
        auth_token: AuthToken,
        space_slug: str,
        limit: int = 50,
        offset: int = 0,
        filter_id: str | None = None,
        adhoc_query: str | None = None,
    ) -> PaginationResult[Note]:
        """Get paginated notes in space (members only), optionally filtered."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        # Get current user to pass for $me substitution
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.note.list_notes(space.id, limit, offset, filter_id, adhoc_query, current_user.id)

    async def get_note_by_number(self, auth_token: AuthToken, space_slug: str, number: int) -> Note:
        """Get specific note by number (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.note.get_note_by_number(space.id, number)

    async def create_note(self, auth_token: AuthToken, space_slug: str, raw_fields: dict[str, str]) -> Note:
        """Create note with custom fields (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.note.create_note(space.id, current_user.id, raw_fields)

    async def update_note_fields(
        self, auth_token: AuthToken, space_slug: str, note_number: int, raw_fields: dict[str, str]
    ) -> Note:
        """Update specific note fields (partial update, members only)."""
        space, note = await self._resolve_note(space_slug, note_number)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.note.update_note_fields(note.id, raw_fields, current_user.id)

    async def get_note_comments(
        self, auth_token: AuthToken, space_slug: str, note_number: int, limit: int = 50, offset: int = 0
    ) -> PaginationResult[Comment]:
        """Get paginated comments for note (members only)."""
        space, note = await self._resolve_note(space_slug, note_number)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.comment.get_note_comments(note.id, limit, offset)

    async def create_comment(self, auth_token: AuthToken, space_slug: str, note_number: int, content: str) -> Comment:
        """Add comment to note (members only)."""
        space, note = await self._resolve_note(space_slug, note_number)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        current_user = await self._core.services.session.get_authenticated_user(auth_token)
        return await self._core.services.comment.create_comment(note.id, space.id, current_user.id, content)

    async def get_current_user(self, auth_token: AuthToken) -> UserView:
        """Get current authenticated user profile."""
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return UserView.from_domain(current_user)

    async def change_password(self, auth_token: AuthToken, old_password: str, new_password: str) -> None:
        """Change password for current user."""
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        await self._core.services.user.change_password(current_user.id, old_password, new_password)

    async def add_space_member(self, auth_token: AuthToken, space_slug: str, username: str) -> Space:
        """Add a member to a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        user = self._resolve_user(username)
        return await self._core.services.space.add_member(space.id, user.id)

    async def remove_space_member(self, auth_token: AuthToken, space_slug: str, username: str) -> None:
        """Remove a member from a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        user = self._resolve_user(username)
        await self._core.services.space.remove_member(space.id, user.id)

    async def update_space_template(
        self, auth_token: AuthToken, space_slug: str, template_name: str, template_content: str | None
    ) -> Space:
        """Update a specific template for a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.update_template(space.id, template_name, template_content)

    async def update_space_list_fields(self, auth_token: AuthToken, space_slug: str, field_ids: list[str]) -> Space:
        """Update the list_fields for a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.update_list_fields(space.id, field_ids)

    async def update_space_hidden_create_fields(self, auth_token: AuthToken, space_slug: str, field_ids: list[str]) -> Space:
        """Update the hidden_create_fields for a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.update_hidden_create_fields(space.id, field_ids)

    async def update_space_title(self, auth_token: AuthToken, space_slug: str, title: str) -> Space:
        """Update the title of a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.update_title(space.id, title)

    async def update_space_description(self, auth_token: AuthToken, space_slug: str, description: str) -> Space:
        """Update the description of a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.update_description(space.id, description)

    async def update_space_slug(self, auth_token: AuthToken, space_slug: str, new_slug: str) -> Space:
        """Update the slug of a space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.space.update_slug(space.id, new_slug)

    async def delete_space(self, auth_token: AuthToken, space_slug: str) -> None:
        """Delete a space and all its data (admin only)."""
        await self._core.services.access.ensure_admin(auth_token)
        space = self._resolve_space(space_slug)

        # Delete in order: comments first (most dependent), then notes, counters, and finally the space
        await self._core.services.comment.delete_comments_by_space(space.id)
        await self._core.services.note.delete_notes_by_space(space.id)
        await self._core.services.counter.delete_counters_by_space(space.id)
        await self._core.services.space.delete_space(space.id)

    async def export_space(self, auth_token: AuthToken, space_slug: str, include_data: bool = False) -> ExportData:
        """Export a space configuration (member only).

        Args:
            auth_token: Authentication token
            space_slug: Space slug to export
            include_data: If True, include notes and comments data
        """
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.export.export_space(space_slug, include_data)

    async def import_space(
        self, auth_token: AuthToken, export_data: ExportData, new_slug: str | None = None, create_missing_users: bool = False
    ) -> Space:
        """Import a space configuration (authenticated only)."""
        current_user = await self._core.services.access.ensure_authenticated(auth_token)
        return await self._core.services.export.import_space(export_data, new_slug, create_missing_users, current_user.id)

    async def remove_field_from_space(self, auth_token: AuthToken, space_slug: str, field_id: str) -> None:
        """Remove field from space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        await self._core.services.field.remove_field_from_space(space.id, field_id)

    async def add_filter_to_space(self, auth_token: AuthToken, space_slug: str, filter: Filter) -> Space:
        """Add custom filter to space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        await self._core.services.filter.add_filter_to_space(space.id, filter)
        return self._resolve_space(space_slug)

    async def remove_filter_from_space(self, auth_token: AuthToken, space_slug: str, filter_id: str) -> None:
        """Remove filter from space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        await self._core.services.filter.remove_filter_from_space(space.id, filter_id)

    # === Telegram integration ===
    async def get_telegram_integration(self, auth_token: AuthToken, space_slug: str) -> TelegramIntegration | None:
        """Get Telegram integration for space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.telegram.get_telegram_integration(space.id)

    async def create_telegram_integration(
        self, auth_token: AuthToken, space_slug: str, bot_token: str, chat_id: str
    ) -> TelegramIntegration:
        """Create Telegram integration for space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.telegram.create_telegram_integration(space.id, bot_token, chat_id)

    async def update_telegram_integration(
        self,
        auth_token: AuthToken,
        space_slug: str,
        bot_token: str | None = None,
        chat_id: str | None = None,
        is_enabled: bool | None = None,
    ) -> TelegramIntegration:
        """Update Telegram integration for space (members only).

        Parameters are optional (None) to support partial updates - only fields
        provided will be updated, while None values are ignored."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.telegram.update_telegram_integration(space.id, bot_token, chat_id, is_enabled)

    async def delete_telegram_integration(self, auth_token: AuthToken, space_slug: str) -> None:
        """Delete Telegram integration for space (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        await self._core.services.telegram.delete_telegram_integration(space.id)

    async def update_telegram_notification(
        self,
        auth_token: AuthToken,
        space_slug: str,
        event_type: TelegramEventType,
        enabled: bool,
        template: str,
    ) -> TelegramNotificationConfig:
        """Update notification configuration for a specific event type (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.telegram.update_notification_config(space.id, event_type, enabled, template)

    async def test_telegram_integration(self, auth_token: AuthToken, space_slug: str) -> dict[TelegramEventType, str | None]:
        """Test Telegram integration by sending test messages for all enabled events (members only)."""
        space = self._resolve_space(space_slug)
        await self._core.services.access.ensure_space_member(auth_token, space.id)
        return await self._core.services.telegram.send_test_message(space.id)

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
