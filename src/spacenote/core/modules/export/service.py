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
from spacenote.core.modules.field.models import FieldType, FieldValueType
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


class ImportContext:
    """Context for tracking state during space import."""

    def __init__(self) -> None:
        self.username_to_id: dict[str, UUID] = {}
        self.note_id_map: dict[int, UUID] = {}
        self.attachment_number_to_id: dict[int, UUID] = {}


class ExportContext:
    """Context for tracking state during space export."""

    def __init__(self) -> None:
        self.note_id_to_number: dict[UUID, int] = {}


class ExportService(Service):
    """Service for exporting and importing space data."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    async def _get_or_create_user(self, username: str, context: ImportContext, space_slug: str) -> UUID:
        """Get existing user or create new one if doesn't exist.

        Updates context.username_to_id cache and returns user ID.
        """
        if username in context.username_to_id:
            return context.username_to_id[username]

        try:
            user = self.core.services.user.get_user_by_username(username)
            user_id = user.id
        except NotFoundError:
            password = generate_secure_password()
            user = await self.core.services.user.create_user(username, password)
            user_id = user.id
            logger.info(
                "import_created_user",
                username=username,
                space_slug=space_slug,
                password_length=len(password),
            )

        context.username_to_id[username] = user_id
        return user_id

    async def _export_notes(self, space: Space, context: ExportContext) -> list[ExportNote]:
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
                    except ValueError:
                        raise ValidationError(
                            f"Note {note.number} has invalid USER field '{field.id}' value: {exported_fields[field.id]!r}. "
                            f"Expected UUID. Data corruption detected."
                        ) from None
                    try:
                        field_user = self.core.services.user.get_user(field_user_id)
                        exported_fields[field.id] = field_user.username
                    except NotFoundError:
                        raise ValidationError(
                            f"Note {note.number} has USER field '{field.id}' referencing "
                            f"non-existent user {field_user_id}. Data corruption detected."
                        ) from None
                elif field.type == FieldType.IMAGE and field.id in exported_fields and exported_fields[field.id]:
                    try:
                        attachment_id = UUID(str(exported_fields[field.id]))
                    except ValueError:
                        raise ValidationError(
                            f"Note {note.number} has invalid IMAGE field '{field.id}' value: {exported_fields[field.id]!r}. "
                            f"Expected UUID. Data corruption detected."
                        ) from None
                    try:
                        attachment = await self.core.services.attachment.get_attachment(attachment_id)
                        exported_fields[field.id] = attachment.number
                    except NotFoundError:
                        raise ValidationError(
                            f"Note {note.number} has IMAGE field '{field.id}' referencing "
                            f"non-existent attachment {attachment_id}. Data corruption detected."
                        ) from None

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
            context.note_id_to_number[note.id] = note.number

        return export_notes

    async def _export_comments(self, space: Space, context: ExportContext) -> list[ExportComment]:
        """Export comments for a space."""
        all_comments = await self.core.services.comment.get_space_comments(space.id)
        export_comments = []

        for comment in all_comments:
            comment_user = self.core.services.user.get_user(comment.user_id)
            note_number = context.note_id_to_number.get(comment.note_id)
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

    async def _export_attachments(self, space: Space, context: ExportContext) -> list[ExportAttachment]:
        """Export attachments for a space."""
        all_attachments = await self.core.services.attachment.list_space_attachments(space.id)
        export_attachments = []

        for attachment in all_attachments:
            attachment_user = self.core.services.user.get_user(attachment.user_id)

            attachment_note_number = None
            if attachment.note_id is not None:
                attachment_note_number = context.note_id_to_number.get(attachment.note_id)
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

        member_usernames = [self.core.services.user.get_user(member_id).username for member_id in space.members]

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
            context = ExportContext()
            export_notes = await self._export_notes(space, context)
            export_comments = await self._export_comments(space, context)
            export_attachments = await self._export_attachments(space, context)

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

    async def _import_space_metadata(self, export_data: ExportData, slug: str, first_member_id: UUID) -> Space:
        """Create space with basic metadata."""
        return await self.core.services.space.create_space(
            slug=slug,
            title=export_data.space.title,
            description=export_data.space.description,
            member=first_member_id,
        )

    async def _ensure_members(
        self, export_data: ExportData, slug: str, current_user_id: UUID | None, context: ImportContext
    ) -> list[UUID]:
        """Ensure all members exist and return member IDs.

        Creates missing users and populates context.username_to_id.
        """
        member_ids = []
        for username in export_data.space.members:
            user_id = await self._get_or_create_user(username, context, slug)
            member_ids.append(user_id)

        if current_user_id and current_user_id not in member_ids:
            member_ids.append(current_user_id)

        return member_ids

    async def _import_space_configuration(self, space_id: UUID, export_data: ExportData) -> None:
        """Import space configuration: fields, templates, filters, telegram."""
        if export_data.space.fields:
            for field in export_data.space.fields:
                await self.core.services.field.add_field_to_space(space_id, field)

        if export_data.space.templates.note_detail:
            await self.core.services.space.update_template(space_id, "note_detail", export_data.space.templates.note_detail)
        if export_data.space.templates.note_list:
            await self.core.services.space.update_template(space_id, "note_list", export_data.space.templates.note_list)

        if export_data.space.list_fields:
            await self.core.services.space.update_list_fields(space_id, export_data.space.list_fields)

        if export_data.space.hidden_create_fields:
            await self.core.services.space.update_hidden_create_fields(space_id, export_data.space.hidden_create_fields)

        if export_data.space.comment_editable_fields:
            await self.core.services.space.update_comment_editable_fields(space_id, export_data.space.comment_editable_fields)

        if export_data.space.filters:
            for filter_def in export_data.space.filters:
                await self.core.services.filter.add_filter_to_space(space_id, filter_def)

        if export_data.space.default_filter:
            await self.core.services.space.update_default_filter(space_id, export_data.space.default_filter)

        if export_data.space.telegram:
            await self.core.services.telegram.create_telegram_integration(space_id=space_id, chat_id="")
            await self.core.services.telegram.update_telegram_integration(space_id=space_id, is_enabled=False)
            for event_type, config in export_data.space.telegram.notifications.items():
                await self.core.services.telegram.update_notification_config(
                    space_id=space_id,
                    event_type=event_type,
                    enabled=config.enabled,
                    template=config.template,
                )

    async def _convert_user_field_to_id(self, field_value: FieldValueType, context: ImportContext, slug: str) -> UUID | None:
        """Convert USER field username to UUID."""
        if not isinstance(field_value, str):
            return None
        return await self._get_or_create_user(field_value, context, slug)

    async def _import_notes(self, space_id: UUID, export_data: ExportData, context: ImportContext, slug: str) -> int:
        """Import notes and return max note number."""
        if not export_data.notes:
            return 0

        logger.info("import_notes_start", space_id=space_id, count=len(export_data.notes))
        max_note_number = 0

        for export_note in export_data.notes:
            user_id = await self._get_or_create_user(export_note.username, context, slug)

            imported_fields = dict(export_note.fields)
            for field in export_data.space.fields:
                field_value = imported_fields.get(field.id)
                if field_value is None:
                    continue

                if field.type == FieldType.USER:
                    converted_id = await self._convert_user_field_to_id(field_value, context, slug)
                    if converted_id:
                        imported_fields[field.id] = converted_id

            converted_note = ExportNote(
                number=export_note.number,
                username=export_note.username,
                created_at=export_note.created_at,
                edited_at=export_note.edited_at,
                commented_at=export_note.commented_at,
                activity_at=export_note.activity_at,
                fields=imported_fields,
            )

            imported_note = await self._import_note(space_id, converted_note, user_id)
            context.note_id_map[export_note.number] = imported_note.id
            max_note_number = max(max_note_number, export_note.number)

        logger.info(
            "import_notes_complete",
            space_id=space_id,
            imported=len(context.note_id_map),
            max_number=max_note_number,
        )
        return max_note_number

    async def _import_attachments(self, space_id: UUID, export_data: ExportData, context: ImportContext, slug: str) -> int:
        """Import attachments and return max attachment number."""
        if not export_data.attachments:
            return 0

        logger.info("import_attachments_start", space_id=space_id, count=len(export_data.attachments))
        attachments_collection = self.database.get_collection("attachments")
        max_attachment_number = 0

        for export_attachment in export_data.attachments:
            user_id = context.username_to_id.get(export_attachment.username)
            if not user_id:
                logger.warning(
                    "import_skip_attachment_missing_user",
                    attachment_number=export_attachment.number,
                    username=export_attachment.username,
                    space_slug=slug,
                )
                continue

            note_id = None
            if export_attachment.note_number is not None:
                note_id = context.note_id_map.get(export_attachment.note_number)
                if not note_id:
                    logger.warning(
                        "import_skip_attachment_missing_note",
                        attachment_number=export_attachment.number,
                        note_number=export_attachment.note_number,
                        space_slug=slug,
                    )
                    continue

            attachment = Attachment(
                space_id=space_id,
                note_id=note_id,
                user_id=user_id,
                number=export_attachment.number,
                filename=export_attachment.filename,
                size=export_attachment.size,
                mime_type=export_attachment.mime_type,
                created_at=export_attachment.created_at,
            )
            await attachments_collection.insert_one(attachment.to_mongo())
            context.attachment_number_to_id[export_attachment.number] = attachment.id
            max_attachment_number = max(max_attachment_number, export_attachment.number)

        logger.info(
            "import_attachments_complete",
            space_id=space_id,
            imported=len(context.attachment_number_to_id),
            max_number=max_attachment_number,
        )
        return max_attachment_number

    async def _update_image_field_references(self, space_id: UUID, export_data: ExportData, context: ImportContext) -> None:
        """Update IMAGE field values in notes to reference attachment UUIDs."""
        if not context.note_id_map or not export_data.space.fields or not export_data.notes:
            return

        image_fields = [field for field in export_data.space.fields if field.type == FieldType.IMAGE]
        if not image_fields:
            return

        notes_collection = self.database.get_collection("notes")
        updated_notes = 0

        for note_number, note_id in context.note_id_map.items():
            source_note = next((n for n in export_data.notes if n.number == note_number), None)
            if source_note is None:
                continue

            fields_to_update = {}
            for field in image_fields:
                field_value = source_note.fields.get(field.id)
                if field_value is not None and isinstance(field_value, int):
                    new_attachment_id = context.attachment_number_to_id.get(field_value)
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
            logger.info("import_image_fields_updated", space_id=space_id, notes_updated=updated_notes)

    async def _import_comments(self, space_id: UUID, export_data: ExportData, context: ImportContext, slug: str) -> int:
        """Import comments and return count of imported comments."""
        if not export_data.comments:
            return 0

        logger.info("import_comments_start", space_id=space_id, count=len(export_data.comments))
        comments_imported = 0

        for export_comment in export_data.comments:
            note_id = context.note_id_map.get(export_comment.note_number)
            if not note_id:
                logger.warning(
                    "import_skip_comment_missing_note",
                    comment_number=export_comment.number,
                    note_number=export_comment.note_number,
                    space_slug=slug,
                )
                continue

            user_id = context.username_to_id.get(export_comment.username)
            if not user_id:
                logger.warning(
                    "import_skip_comment_missing_user",
                    comment_number=export_comment.number,
                    username=export_comment.username,
                    space_slug=slug,
                )
                continue

            await self._import_comment(space_id, note_id, export_comment, user_id)
            comments_imported += 1

        logger.info("import_comments_complete", space_id=space_id, imported=comments_imported)
        return comments_imported

    async def import_space(
        self, export_data: ExportData, new_slug: str | None = None, current_user_id: UUID | None = None
    ) -> Space:
        """Import a space from export data.

        Imports:
        - Basic space info (slug, title, description)
        - Members (creates them if they don't exist)
        - Fields, templates, filters, telegram configuration
        - Notes, attachments, comments (if present in export_data)
        """
        slug = new_slug or export_data.space.slug

        with suppress(NotFoundError):
            self.core.services.space.get_space_by_slug(slug)
            raise ValidationError(f"Space with slug '{slug}' already exists")

        context = ImportContext()

        member_ids = await self._ensure_members(export_data, slug, current_user_id, context)
        space = await self._import_space_metadata(export_data, slug, member_ids[0])

        for member_id in member_ids[1:]:
            await self.core.services.space.add_member(space.id, member_id)

        await self._import_space_configuration(space.id, export_data)

        max_note_number = await self._import_notes(space.id, export_data, context, slug)
        if max_note_number > 0:
            await self.core.services.counter.set_sequence(space.id, CounterType.NOTE, max_note_number)

        max_attachment_number = await self._import_attachments(space.id, export_data, context, slug)
        if max_attachment_number > 0:
            await self.core.services.counter.set_sequence(space.id, CounterType.ATTACHMENT, max_attachment_number)

        await self._update_image_field_references(space.id, export_data, context)

        comments_imported = await self._import_comments(space.id, export_data, context, slug)

        space = self.core.services.space.get_space(space.id)
        logger.info(
            "space_imported",
            slug=slug,
            member_count=len(member_ids),
            field_count=len(export_data.space.fields),
            note_count=len(context.note_id_map),
            comment_count=comments_imported,
        )

        return space
