"""Export/import service for space data."""

import secrets
import string
from contextlib import suppress
from typing import Any

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.export.models import ExportData, ExportSpace
from spacenote.core.modules.space.models import Space
from spacenote.errors import NotFoundError, ValidationError
from spacenote.utils import now

logger = structlog.get_logger(__name__)

SPACENOTE_VERSION = "0.0.1"


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


class ExportService(Service):
    """Service for exporting and importing space data."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    async def export_space(self, space_slug: str) -> ExportData:
        """Export a space with all its configuration."""
        space = self.core.services.space.get_space_by_slug(space_slug)

        member_usernames = []
        for member_id in space.members:
            user = self.core.services.user.get_user(member_id)
            member_usernames.append(user.username)

        export_space = ExportSpace(
            slug=space.slug,
            title=space.title,
            description=space.description,
            members=member_usernames,
            fields=space.fields,
            list_fields=space.list_fields,
            hidden_create_fields=space.hidden_create_fields,
            filters=space.filters,
            templates=space.templates,
        )

        return ExportData(
            space=export_space,
            exported_at=now(),
            spacenote_version=SPACENOTE_VERSION,
        )

    async def import_space(
        self, export_data: ExportData, new_slug: str | None = None, create_missing_users: bool = False
    ) -> Space:
        """Import a space from export data.

        Currently imports:
        - Basic space info (slug, title, description)
        - Members (those that exist in the system, or creates them if create_missing_users=True)
        - Fields
        - Templates

        TODO: Import list_fields, hidden_create_fields, filters when SpaceService supports updating them.
        """
        slug = new_slug or export_data.space.slug

        with suppress(NotFoundError):
            self.core.services.space.get_space_by_slug(slug)
            raise ValidationError(f"Space with slug '{slug}' already exists")

        member_ids = []
        for username in export_data.space.members:
            try:
                user = self.core.services.user.get_user_by_username(username)
                member_ids.append(user.id)
            except NotFoundError:
                if create_missing_users:
                    # Generate secure random password
                    password = generate_secure_password()
                    user = await self.core.services.user.create_user(username, password)
                    member_ids.append(user.id)
                    logger.info(
                        "import_created_user",
                        username=username,
                        space_slug=slug,
                        password_length=len(password),
                    )
                else:
                    logger.warning("import_skip_missing_user", username=username, space_slug=slug)
                    continue

        if not member_ids:
            raise ValidationError("Cannot import space without any valid members")

        first_member = member_ids[0]
        space = await self.core.services.space.create_space(
            slug=slug,
            title=export_data.space.title,
            description=export_data.space.description,
            member=first_member,
        )

        for member_id in member_ids[1:]:
            await self.core.services.space.add_member(space.id, member_id)

        if export_data.space.fields:
            for field in export_data.space.fields:
                await self.core.services.space.add_field(space.id, field)

        if export_data.space.templates.note_detail:
            await self.core.services.space.update_template(space.id, "note_detail", export_data.space.templates.note_detail)
        if export_data.space.templates.note_list:
            await self.core.services.space.update_template(space.id, "note_list", export_data.space.templates.note_list)

        space = self.core.services.space.get_space(space.id)
        logger.info(
            "space_imported",
            slug=slug,
            member_count=len(member_ids),
            field_count=len(export_data.space.fields),
        )

        return space
