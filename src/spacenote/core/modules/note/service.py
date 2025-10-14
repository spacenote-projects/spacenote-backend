from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.counter.models import CounterType
from spacenote.core.modules.field.models import FieldType
from spacenote.core.modules.filter.adhoc import parse_adhoc_query
from spacenote.core.modules.filter.models import SYSTEM_FIELD_DEFINITIONS
from spacenote.core.modules.filter.query_builder import build_mongo_query
from spacenote.core.modules.note.models import Note
from spacenote.core.modules.telegram.models import TelegramEventType
from spacenote.core.pagination import PaginationResult
from spacenote.errors import NotFoundError
from spacenote.utils import now

logger = structlog.get_logger(__name__)


class NoteService(Service):
    """Manages notes with custom fields in spaces."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("notes")

    async def on_start(self) -> None:
        """Create indexes for space/number lookup and sorting."""
        await self._collection.create_index([("space_id", 1), ("number", 1)], unique=True)
        await self._collection.create_index([("space_id", 1)])

    async def list_notes(
        self,
        space_id: UUID,
        limit: int = 50,
        offset: int = 0,
        filter_id: str | None = None,
        adhoc_query: str | None = None,
        current_user_id: UUID | None = None,
    ) -> PaginationResult[Note]:
        """Get paginated notes in space, optionally filtered.

        Args:
            space_id: The space ID to list notes from
            limit: Maximum number of notes to return
            offset: Number of notes to skip
            filter_id: Optional filter id to apply
            adhoc_query: Optional ad-hoc query string (field:operator:value,...)
            current_user_id: The ID of the current logged-in user (optional, for $me substitution)

        Returns:
            Paginated list of notes
        """
        # Build base query from saved filter
        if filter_id:
            query = self.core.services.filter.build_mongo_query(space_id, filter_id, current_user_id)
            sort_spec = self.core.services.filter.build_mongo_sort(space_id, filter_id)
        else:
            query = {"space_id": space_id}
            sort_spec = [("number", -1)]

        # Parse and merge adhoc query if provided
        if adhoc_query:
            space = self.core.services.space.get_space(space_id)
            members = [self.core.services.user.get_user(uid) for uid in space.members]
            adhoc_conditions = parse_adhoc_query(adhoc_query, space, members)

            # Build MongoDB query from adhoc conditions
            field_definitions = {}
            for condition in adhoc_conditions:
                field_def = space.get_field(condition.field)
                if field_def is None:
                    field_def = SYSTEM_FIELD_DEFINITIONS().get(condition.field)
                if field_def is not None:
                    field_definitions[condition.field] = field_def

            adhoc_query_dict = build_mongo_query(adhoc_conditions, field_definitions, space_id, current_user_id)
            adhoc_query_dict.pop("space_id", None)

            # Merge adhoc conditions with base query using AND logic
            if adhoc_query_dict:
                if "$and" in query:
                    # Already has $and - append new conditions
                    and_list = query["$and"]
                    if isinstance(and_list, list):
                        for field_path, condition in adhoc_query_dict.items():
                            if field_path == "$and" and isinstance(condition, list):
                                and_list.extend(condition)
                            else:
                                and_list.append({field_path: condition})
                else:
                    # Create $and with existing and new conditions
                    existing_conditions = [{k: v} for k, v in query.items() if k != "space_id"]
                    new_conditions = []
                    for field_path, condition in adhoc_query_dict.items():
                        if field_path == "$and" and isinstance(condition, list):
                            new_conditions.extend(condition)
                        else:
                            new_conditions.append({field_path: condition})

                    if existing_conditions or new_conditions:
                        query = {"space_id": space_id, "$and": existing_conditions + new_conditions}

        # Get total count
        total = await self._collection.count_documents(query)

        # Get paginated items with dynamic sorting
        cursor = self._collection.find(query)
        for field, direction in sort_spec:
            cursor = cursor.sort(field, direction)
        cursor = cursor.skip(offset).limit(limit)

        docs = await cursor.to_list()
        items = [Note.model_validate(doc) for doc in docs]

        logger.debug(
            "list_notes",
            space_id=space_id,
            adhoc_query=adhoc_query,
            query=query,
            sort=sort_spec,
            total=total,
            limit=limit,
            offset=offset,
            returned=len(items),
        )
        return PaginationResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_note(self, note_id: UUID) -> Note:
        """Get note by ID."""
        doc = await self._collection.find_one({"_id": note_id})
        if not doc:
            raise NotFoundError(f"Note not found: {note_id}")
        return Note.model_validate(doc)

    async def get_note_by_number(self, space_id: UUID, number: int) -> Note:
        """Get note by space and sequential number."""
        doc = await self._collection.find_one({"space_id": space_id, "number": number})
        if not doc:
            raise NotFoundError(f"Note not found: space_id={space_id}, number={number}")
        return Note.model_validate(doc)

    async def create_note(self, space_id: UUID, user_id: UUID, raw_fields: dict[str, str]) -> Note:
        """Create note from raw fields."""
        space = self.core.services.space.get_space(space_id)
        if user_id not in space.members:
            raise NotFoundError(f"User {user_id} is not a member of space {space_id}")

        parsed_fields = self.core.services.field.parse_raw_fields(space_id, raw_fields, current_user_id=user_id)

        # Validate IMAGE field attachments BEFORE creating note in DB
        for field in space.fields:
            if field.type == FieldType.IMAGE and field.id in parsed_fields:
                attachment_id = parsed_fields[field.id]
                if attachment_id is not None and isinstance(attachment_id, UUID):
                    await self.core.services.image.validate_image_attachment(attachment_id)

        next_number = await self.core.services.counter.get_next_sequence(space_id, CounterType.NOTE)
        timestamp = now()
        res = await self._collection.insert_one(
            Note(
                space_id=space_id,
                number=next_number,
                user_id=user_id,
                created_at=timestamp,
                activity_at=timestamp,
                fields=parsed_fields,
            ).to_mongo()
        )
        note = await self.get_note(res.inserted_id)

        # Process IMAGE field attachments (attach files and generate previews in background)
        self.core.services.image.process_note_images(note.id)

        # Send Telegram notification in the background
        self.core.services.telegram.send_notification(
            event_type=TelegramEventType.NOTE_CREATED, note=note, user_id=user_id, space_id=space_id
        )

        return note

    async def update_note_fields(self, note_id: UUID, raw_fields: dict[str, str], current_user_id: UUID | None = None) -> Note:
        """Update specific note fields with validation (partial update).

        Only the fields provided in raw_fields are updated. All other existing
        fields remain unchanged. This is efficient for large field sets.

        Args:
            note_id: The ID of the note to update
            raw_fields: Dictionary of field names to new values (partial update)
            current_user_id: The current user ID for field validation context

        Returns:
            The updated note with all fields
        """
        logger.debug("update_note_fields", note_id=note_id, raw_fields=raw_fields, current_user_id=current_user_id)
        note = await self.get_note(note_id)
        parsed_fields = self.core.services.field.parse_raw_fields(note.space_id, raw_fields, current_user_id, partial=True)

        # Validate IMAGE field attachments BEFORE updating note in DB
        space = self.core.services.space.get_space(note.space_id)
        for field in space.fields:
            if field.type == FieldType.IMAGE and field.id in parsed_fields:
                attachment_id = parsed_fields[field.id]
                if attachment_id is not None and isinstance(attachment_id, UUID):
                    await self.core.services.image.validate_image_attachment(attachment_id)

        # Build update document with only the specific fields to update
        timestamp = now()
        update_doc: dict[str, Any] = {"edited_at": timestamp, "activity_at": timestamp}
        for field_name, field_value in parsed_fields.items():
            update_doc[f"fields.{field_name}"] = field_value

        await self._collection.update_one({"_id": note_id}, {"$set": update_doc})

        updated_note = await self.get_note(note_id)

        # Process IMAGE field attachments (attach files and generate previews in background)
        self.core.services.image.process_note_images(note.id)

        # Send Telegram notification in the background if we have user context
        if current_user_id:
            self.core.services.telegram.send_notification(
                event_type=TelegramEventType.NOTE_UPDATED,
                note=updated_note,
                user_id=current_user_id,
                space_id=updated_note.space_id,
                updated_fields=parsed_fields,
            )

        return updated_note

    async def delete_notes_by_space(self, space_id: UUID) -> int:
        """Delete all notes in a space and return count of deleted notes."""
        result = await self._collection.delete_many({"space_id": space_id})
        return result.deleted_count
