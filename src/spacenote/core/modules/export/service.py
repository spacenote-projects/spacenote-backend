"""Export/import service for space data."""

import secrets
import string
from contextlib import suppress
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.counter.models import CounterType
from spacenote.core.modules.export.models import ExportComment, ExportData, ExportNote, ExportSpace
from spacenote.core.modules.note.models import Note
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

    async def export_space(self, space_slug: str, include_data: bool = False) -> ExportData:
        """Export a space with all its configuration and optionally data.

        Args:
            space_slug: The slug of the space to export
            include_data: If True, include all notes and comments
        """
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

        export_notes = None
        export_comments = None

        if include_data:
            # Get all notes for the space (no pagination)
            all_notes = await self.core.services.note.list_notes(space.id, limit=10000, offset=0)
            export_notes = []

            for note in all_notes.items:
                # Get username for note creator
                note_user = self.core.services.user.get_user(note.user_id)
                export_note = ExportNote(
                    number=note.number,
                    username=note_user.username,
                    created_at=note.created_at,
                    edited_at=note.edited_at,
                    commented_at=note.commented_at,
                    activity_at=note.activity_at,
                    fields=note.fields,
                )
                export_notes.append(export_note)

            # Get all comments for the space
            all_comments = await self.core.services.comment.get_space_comments(space.id)
            export_comments = []

            # Build note_id to number mapping for comments
            note_id_to_number = {note.id: note.number for note in all_notes.items}

            for comment in all_comments:
                # Get username for comment author
                comment_user = self.core.services.user.get_user(comment.user_id)
                # Get note number from note_id
                note_number = note_id_to_number.get(comment.note_id)
                if note_number is None:
                    # Skip orphaned comments
                    logger.warning("export_skip_orphan_comment", comment_id=comment.id, note_id=comment.note_id)
                    continue

                export_comment = ExportComment(
                    note_number=note_number,
                    number=comment.number,
                    username=comment_user.username,
                    content=comment.content,
                    created_at=comment.created_at,
                    edited_at=comment.edited_at,
                )
                export_comments.append(export_comment)

            logger.info(
                "export_with_data",
                space_slug=space_slug,
                note_count=len(export_notes),
                comment_count=len(export_comments),
            )

        return ExportData(
            space=export_space,
            notes=export_notes,
            comments=export_comments,
            exported_at=now(),
            spacenote_version=SPACENOTE_VERSION,
        )

    async def _import_note(self, space_id: UUID, export_note: ExportNote, user_id: UUID) -> Note:
        """Import a note with preserved number and timestamps.

        Args:
            space_id: The space to import the note into
            export_note: The exported note data
            user_id: The user ID of the note creator
        """
        notes_collection = self.database.get_collection("notes")
        note = Note(
            space_id=space_id,
            number=export_note.number,
            user_id=user_id,
            created_at=export_note.created_at,
            edited_at=export_note.edited_at,
            commented_at=export_note.commented_at,
            activity_at=export_note.activity_at,
            fields=export_note.fields,
        )
        await notes_collection.insert_one(note.to_mongo())
        return note

    async def _import_comment(self, space_id: UUID, note_id: UUID, export_comment: ExportComment, user_id: UUID) -> Comment:
        """Import a comment with preserved number and timestamps.

        Args:
            space_id: The space ID
            note_id: The note this comment belongs to
            export_comment: The exported comment data
            user_id: The user ID of the comment author
        """
        comments_collection = self.database.get_collection("comments")
        comment = Comment(
            note_id=note_id,
            space_id=space_id,
            user_id=user_id,
            number=export_comment.number,
            content=export_comment.content,
            created_at=export_comment.created_at,
            edited_at=export_comment.edited_at,
        )
        await comments_collection.insert_one(comment.to_mongo())
        return comment

    async def import_space(  # noqa: PLR0915
        self,
        export_data: ExportData,
        new_slug: str | None = None,
        create_missing_users: bool = False,
        current_user_id: UUID | None = None,
    ) -> Space:
        """Import a space from export data.

        Imports:
        - Basic space info (slug, title, description)
        - Members (those that exist in the system, or creates them if create_missing_users=True)
        - Fields
        - Templates
        - List fields configuration
        - Hidden create fields configuration
        - Filters
        - Notes (if present in export_data)
        - Comments (if present in export_data)
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

        # Add current user to members if not already present
        if current_user_id and current_user_id not in member_ids:
            member_ids.append(current_user_id)

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
                await self.core.services.field.add_field_to_space(space.id, field)

        if export_data.space.templates.note_detail:
            await self.core.services.space.update_template(space.id, "note_detail", export_data.space.templates.note_detail)
        if export_data.space.templates.note_list:
            await self.core.services.space.update_template(space.id, "note_list", export_data.space.templates.note_list)

        # Import list_fields if present
        if export_data.space.list_fields:
            await self.core.services.space.update_list_fields(space.id, export_data.space.list_fields)
            logger.info("import_list_fields", space_id=space.id, count=len(export_data.space.list_fields))

        # Import hidden_create_fields if present
        if export_data.space.hidden_create_fields:
            await self.core.services.space.update_hidden_create_fields(space.id, export_data.space.hidden_create_fields)
            logger.info("import_hidden_create_fields", space_id=space.id, count=len(export_data.space.hidden_create_fields))

        # Import filters if present
        if export_data.space.filters:
            for filter_def in export_data.space.filters:
                await self.core.services.filter.add_filter_to_space(space.id, filter_def)
            logger.info("import_filters", space_id=space.id, count=len(export_data.space.filters))

        # Import notes if present
        note_id_map = {}  # Maps note number to note ID for comment import
        max_note_number = 0
        username_to_id = {}  # Build username to user_id mapping
        comments_imported = 0  # Track imported comments

        # Build username to user_id mapping
        for username in export_data.space.members:
            try:
                user = self.core.services.user.get_user_by_username(username)
                username_to_id[username] = user.id
            except NotFoundError:
                if not create_missing_users:
                    # User was not created, skip their content
                    continue

        if export_data.notes:
            logger.info("import_notes_start", space_id=space.id, count=len(export_data.notes))

            for export_note in export_data.notes:
                # Get user ID for note creator
                user_id = username_to_id.get(export_note.username)
                if not user_id:
                    logger.warning(
                        "import_skip_note_missing_user",
                        note_number=export_note.number,
                        username=export_note.username,
                        space_slug=slug,
                    )
                    continue

                # Import note directly with its fields (already validated during export)
                imported_note = await self._import_note(space.id, export_note, user_id)
                note_id_map[export_note.number] = imported_note.id
                max_note_number = max(max_note_number, export_note.number)

            # Update counter to max note number to prevent conflicts
            if max_note_number > 0:
                await self.core.services.counter.set_sequence(space.id, CounterType.NOTE, max_note_number)

            logger.info(
                "import_notes_complete",
                space_id=space.id,
                imported=len(note_id_map),
                max_number=max_note_number,
            )

        # Import comments if present
        if export_data.comments:
            logger.info("import_comments_start", space_id=space.id, count=len(export_data.comments))
            for export_comment in export_data.comments:
                # Get note ID from number
                note_id = note_id_map.get(export_comment.note_number)
                if not note_id:
                    logger.warning(
                        "import_skip_comment_missing_note",
                        comment_number=export_comment.number,
                        note_number=export_comment.note_number,
                        space_slug=slug,
                    )
                    continue

                # Get user ID for comment author
                user_id = username_to_id.get(export_comment.username)
                if not user_id:
                    logger.warning(
                        "import_skip_comment_missing_user",
                        comment_number=export_comment.number,
                        username=export_comment.username,
                        space_slug=slug,
                    )
                    continue

                await self._import_comment(space.id, note_id, export_comment, user_id)
                comments_imported += 1

            logger.info(
                "import_comments_complete",
                space_id=space.id,
                imported=comments_imported,
            )

        space = self.core.services.space.get_space(space.id)
        logger.info(
            "space_imported",
            slug=slug,
            member_count=len(member_ids),
            field_count=len(export_data.space.fields),
            note_count=len(note_id_map) if export_data.notes else 0,
            comment_count=comments_imported if export_data.comments else 0,
        )

        return space
