"""Export/import service for space data."""

import secrets
import string
from contextlib import suppress
from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.attachment.models import Attachment
from spacenote.core.modules.comment.models import Comment
from spacenote.core.modules.counter.models import CounterType
from spacenote.core.modules.export.models import (
    ExportAttachment,
    ExportComment,
    ExportData,
    ExportNote,
    ExportSpace,
    ExportTelegramConfig,
)
from spacenote.core.modules.field.models import FieldType
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

    async def _export_notes(self, space: Space, note_id_to_number: dict[UUID, int]) -> tuple[list[ExportNote], dict[UUID, int]]:
        """Export notes for a space and build note_id to number mapping."""
        all_notes = await self.core.services.note.get_space_notes(space.id)
        export_notes = []

        for note in all_notes:
            note_user = self.core.services.user.get_user(note.user_id)

            # Convert USER field UUIDs to usernames and IMAGE field UUIDs to attachment numbers
            exported_fields = dict(note.fields)
            for field in space.fields:
                if field.type == FieldType.USER and field.id in exported_fields and exported_fields[field.id]:
                    try:
                        field_user_id = UUID(str(exported_fields[field.id]))
                        field_user = self.core.services.user.get_user(field_user_id)
                        exported_fields[field.id] = field_user.username
                    except (ValueError, NotFoundError):
                        pass
                elif field.type == FieldType.IMAGE and field.id in exported_fields and exported_fields[field.id]:
                    try:
                        attachment_id = UUID(str(exported_fields[field.id]))
                        attachment = await self.core.services.attachment.get_attachment(attachment_id)
                        exported_fields[field.id] = attachment.number
                    except (ValueError, NotFoundError):
                        pass

            export_note = ExportNote(
                number=note.number,
                username=note_user.username,
                created_at=note.created_at,
                edited_at=note.edited_at,
                commented_at=note.commented_at,
                activity_at=note.activity_at,
                fields=exported_fields,
            )
            export_notes.append(export_note)
            note_id_to_number[note.id] = note.number

        return export_notes, note_id_to_number

    async def _export_comments(self, space: Space, note_id_to_number: dict[UUID, int]) -> list[ExportComment]:
        """Export comments for a space."""
        all_comments = await self.core.services.comment.get_space_comments(space.id)
        export_comments = []

        for comment in all_comments:
            comment_user = self.core.services.user.get_user(comment.user_id)
            note_number = note_id_to_number.get(comment.note_id)
            if note_number is None:
                raise ValidationError(
                    f"Comment {comment.id} references non-existent note {comment.note_id}. Data corruption detected."
                )

            export_comment = ExportComment(
                note_number=note_number,
                number=comment.number,
                username=comment_user.username,
                content=comment.content,
                created_at=comment.created_at,
                edited_at=comment.edited_at,
            )
            export_comments.append(export_comment)

        return export_comments

    async def _export_attachments(self, space: Space, note_id_to_number: dict[UUID, int]) -> list[ExportAttachment]:
        """Export attachments for a space."""
        all_attachments = await self.core.services.attachment.list_space_attachments(space.id)
        export_attachments = []

        for attachment in all_attachments:
            attachment_user = self.core.services.user.get_user(attachment.user_id)

            attachment_note_number = None
            if attachment.note_id is not None:
                attachment_note_number = note_id_to_number.get(attachment.note_id)
                if attachment_note_number is None:
                    raise ValidationError(
                        f"Attachment {attachment.id} references non-existent note {attachment.note_id}. Data corruption detected."
                    )

            export_attachment = ExportAttachment(
                number=attachment.number,
                note_number=attachment_note_number,
                username=attachment_user.username,
                filename=attachment.filename,
                size=attachment.size,
                mime_type=attachment.mime_type,
                created_at=attachment.created_at,
            )
            export_attachments.append(export_attachment)

        return export_attachments

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

        telegram_integration = await self.core.services.telegram.get_telegram_integration(space.id)
        export_telegram = None
        if telegram_integration:
            export_telegram = ExportTelegramConfig(
                is_enabled=telegram_integration.is_enabled,
                notifications=telegram_integration.notifications,
            )

        export_space = ExportSpace(
            slug=space.slug,
            title=space.title,
            description=space.description,
            members=member_usernames,
            fields=space.fields,
            list_fields=space.list_fields,
            hidden_create_fields=space.hidden_create_fields,
            comment_editable_fields=space.comment_editable_fields,
            filters=space.filters,
            default_filter=space.default_filter,
            templates=space.templates,
            telegram=export_telegram,
        )

        export_notes = None
        export_comments = None
        export_attachments = None

        if include_data:
            note_id_to_number: dict[UUID, int] = {}
            export_notes, note_id_to_number = await self._export_notes(space, note_id_to_number)
            export_comments = await self._export_comments(space, note_id_to_number)
            export_attachments = await self._export_attachments(space, note_id_to_number)

            logger.info(
                "export_with_data",
                space_slug=space_slug,
                note_count=len(export_notes),
                comment_count=len(export_comments),
                attachment_count=len(export_attachments),
            )

        return ExportData(
            space=export_space,
            notes=export_notes,
            comments=export_comments,
            attachments=export_attachments if include_data else None,
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
        self, export_data: ExportData, new_slug: str | None = None, current_user_id: UUID | None = None
    ) -> Space:
        """Import a space from export data.

        Imports:
        - Basic space info (slug, title, description)
        - Members (creates them if they don't exist)
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
                # Always create missing users
                password = generate_secure_password()
                user = await self.core.services.user.create_user(username, password)
                member_ids.append(user.id)
                logger.info(
                    "import_created_user",
                    username=username,
                    space_slug=slug,
                    password_length=len(password),
                )

        # Add current user to members if not already present
        if current_user_id and current_user_id not in member_ids:
            member_ids.append(current_user_id)

        space = await self.core.services.space.create_space(
            slug=slug, title=export_data.space.title, description=export_data.space.description, member=member_ids[0]
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

        # Import hidden_create_fields if present
        if export_data.space.hidden_create_fields:
            await self.core.services.space.update_hidden_create_fields(space.id, export_data.space.hidden_create_fields)

        # Import comment_editable_fields if present
        if export_data.space.comment_editable_fields:
            await self.core.services.space.update_comment_editable_fields(space.id, export_data.space.comment_editable_fields)

        # Import filters if present
        if export_data.space.filters:
            for filter_def in export_data.space.filters:
                await self.core.services.filter.add_filter_to_space(space.id, filter_def)

        # Import default_filter if present (must be after filters are imported)
        if export_data.space.default_filter:
            await self.core.services.space.update_default_filter(space.id, export_data.space.default_filter)

        # Import telegram integration if present
        if export_data.space.telegram:
            await self.core.services.telegram.create_telegram_integration(
                space_id=space.id,
                chat_id="",
            )
            await self.core.services.telegram.update_telegram_integration(
                space_id=space.id,
                is_enabled=False,
            )
            for event_type, config in export_data.space.telegram.notifications.items():
                await self.core.services.telegram.update_notification_config(
                    space_id=space.id,
                    event_type=event_type,
                    enabled=config.enabled,
                    template=config.template,
                )

        # Import notes if present
        note_id_map = {}  # Maps note number to note ID for comment import
        max_note_number = 0
        username_to_id = {}  # Build username to user_id mapping
        comments_imported = 0  # Track imported comments

        # Build username to user_id mapping from members (all should exist now)
        for username in export_data.space.members:
            user = self.core.services.user.get_user_by_username(username)
            username_to_id[username] = user.id

        if export_data.notes:
            logger.info("import_notes_start", space_id=space.id, count=len(export_data.notes))

            for export_note in export_data.notes:
                # Get user ID for note creator
                user_id = username_to_id.get(export_note.username)
                if not user_id:
                    # Create user if not in members list
                    password = generate_secure_password()
                    user = await self.core.services.user.create_user(export_note.username, password)
                    username_to_id[export_note.username] = user.id
                    user_id = user.id
                    logger.info(
                        "import_created_user",
                        username=export_note.username,
                        space_slug=slug,
                        password_length=len(password),
                    )

                # Convert USER field usernames back to UUIDs and IMAGE field attachment numbers to UUIDs
                imported_fields = dict(export_note.fields)
                for field in export_data.space.fields:
                    if field.type == FieldType.USER and field.id in imported_fields and imported_fields[field.id]:
                        field_value = imported_fields[field.id]
                        if isinstance(field_value, str):
                            field_user_id = username_to_id.get(field_value)
                            if not field_user_id:
                                # Create user if doesn't exist
                                password = generate_secure_password()
                                user = await self.core.services.user.create_user(field_value, password)
                                username_to_id[field_value] = user.id
                                field_user_id = user.id
                                logger.info(
                                    "import_created_user",
                                    username=field_value,
                                    space_slug=slug,
                                    password_length=len(password),
                                )
                            imported_fields[field.id] = field_user_id
                    elif field.type == FieldType.IMAGE and field.id in imported_fields and imported_fields[field.id]:
                        field_value = imported_fields[field.id]
                        if isinstance(field_value, int):
                            # Convert attachment number to UUID (will be mapped after attachments are imported)
                            # For now, keep as number - will convert after attachment import
                            pass

                # Create a new ExportNote with converted fields for import
                converted_note = ExportNote(
                    number=export_note.number,
                    username=export_note.username,
                    created_at=export_note.created_at,
                    edited_at=export_note.edited_at,
                    commented_at=export_note.commented_at,
                    activity_at=export_note.activity_at,
                    fields=imported_fields,
                )

                # Import note with converted fields
                imported_note = await self._import_note(space.id, converted_note, user_id)
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

        # Import attachments if present
        attachment_number_to_id = {}  # Maps attachment number to new attachment UUID
        max_attachment_number = 0

        if export_data.attachments:
            logger.info("import_attachments_start", space_id=space.id, count=len(export_data.attachments))
            attachments_collection = self.database.get_collection("attachments")

            for export_attachment in export_data.attachments:
                # Get user ID for attachment uploader
                user_id = username_to_id.get(export_attachment.username)
                if not user_id:
                    logger.warning(
                        "import_skip_attachment_missing_user",
                        attachment_number=export_attachment.number,
                        username=export_attachment.username,
                        space_slug=slug,
                    )
                    continue

                # Get note ID if attachment belongs to a note
                note_id = None
                if export_attachment.note_number is not None:
                    note_id = note_id_map.get(export_attachment.note_number)
                    if not note_id:
                        logger.warning(
                            "import_skip_attachment_missing_note",
                            attachment_number=export_attachment.number,
                            note_number=export_attachment.note_number,
                            space_slug=slug,
                        )
                        continue

                # Create attachment record with preserved number
                attachment = Attachment(
                    space_id=space.id,
                    note_id=note_id,
                    user_id=user_id,
                    number=export_attachment.number,
                    filename=export_attachment.filename,
                    size=export_attachment.size,
                    mime_type=export_attachment.mime_type,
                    created_at=export_attachment.created_at,
                )
                await attachments_collection.insert_one(attachment.to_mongo())
                attachment_number_to_id[export_attachment.number] = attachment.id
                max_attachment_number = max(max_attachment_number, export_attachment.number)

            # Update attachment counter
            if max_attachment_number > 0:
                await self.core.services.counter.set_sequence(space.id, CounterType.ATTACHMENT, max_attachment_number)

            logger.info(
                "import_attachments_complete",
                space_id=space.id,
                imported=len(attachment_number_to_id),
                max_number=max_attachment_number,
            )

            # Update IMAGE field values in notes with new attachment UUIDs
            # Notes were imported with attachment numbers in IMAGE fields, now convert to UUIDs
            if note_id_map and export_data.space.fields and export_data.notes:
                image_fields = [field for field in export_data.space.fields if field.type == FieldType.IMAGE]
                if image_fields:
                    notes_collection = self.database.get_collection("notes")
                    updated_notes = 0

                    for note_number, note_id in note_id_map.items():
                        # Find the corresponding export note to get attachment numbers
                        source_note: ExportNote | None = next((n for n in export_data.notes if n.number == note_number), None)
                        if source_note is None:
                            continue

                        # Check if any IMAGE fields need remapping
                        fields_to_update = {}
                        for field in image_fields:
                            field_value = source_note.fields.get(field.id)
                            if field_value is not None and isinstance(field_value, int):
                                # Convert attachment number to UUID
                                new_attachment_id = attachment_number_to_id.get(field_value)
                                if new_attachment_id:
                                    fields_to_update[f"fields.{field.id}"] = new_attachment_id
                                else:
                                    logger.warning(
                                        "import_image_field_attachment_not_found",
                                        note_number=note_number,
                                        field_id=field.id,
                                        attachment_number=field_value,
                                    )

                        if fields_to_update:
                            await notes_collection.update_one({"_id": note_id}, {"$set": fields_to_update})
                            updated_notes += 1

                    if updated_notes > 0:
                        logger.info("import_image_fields_updated", space_id=space.id, notes_updated=updated_notes)

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
