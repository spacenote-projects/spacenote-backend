from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.counter.models import CounterType
from spacenote.core.modules.note.models import Note
from spacenote.core.pagination import PaginationResult
from spacenote.errors import NotFoundError
from spacenote.utils import now


class NoteService(Service):
    """Manages notes with custom fields in spaces."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("notes")

    async def on_start(self) -> None:
        """Create indexes for space/number lookup and sorting."""
        await self._collection.create_index([("space_id", 1), ("number", 1)], unique=True)
        await self._collection.create_index([("space_id", 1)])
        await self._collection.create_index([("created_at", -1)])
        await self._collection.create_index([("activity_at", -1)])
        await self._collection.create_index([("commented_at", -1)])

    async def list_notes(self, space_id: UUID, limit: int = 50, offset: int = 0) -> PaginationResult[Note]:
        """Get paginated notes in space, sorted by number descending."""
        query = {"space_id": space_id}

        # Get total count
        total = await self._collection.count_documents(query)

        # Get paginated items
        cursor = self._collection.find(query).sort("number", -1).skip(offset).limit(limit)
        docs = await cursor.to_list()
        items = [Note.model_validate(doc) for doc in docs]

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

    async def create_note(self, space_id: UUID, author_id: UUID, raw_fields: dict[str, str]) -> Note:
        """Create note from raw fields."""
        space = self.core.services.space.get_space(space_id)
        if author_id not in space.members:
            raise NotFoundError(f"User {author_id} is not a member of space {space_id}")

        parsed_fields = self.core.services.field.parse_raw_fields(space_id, raw_fields, current_user_id=author_id)
        next_number = await self.core.services.counter.get_next_sequence(space_id, CounterType.NOTE)
        timestamp = now()
        res = await self._collection.insert_one(
            Note(
                space_id=space_id,
                number=next_number,
                author_id=author_id,
                created_at=timestamp,
                activity_at=timestamp,
                fields=parsed_fields,
            ).to_mongo()
        )
        return await self.get_note(res.inserted_id)

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
        note = await self.get_note(note_id)
        parsed_fields = self.core.services.field.parse_raw_fields(note.space_id, raw_fields, current_user_id, partial=True)

        # Build update document with only the specific fields to update
        timestamp = now()
        update_doc: dict[str, Any] = {"edited_at": timestamp, "activity_at": timestamp}
        for field_name, field_value in parsed_fields.items():
            update_doc[f"fields.{field_name}"] = field_value

        await self._collection.update_one({"_id": note_id}, {"$set": update_doc})

        return await self.get_note(note_id)

    async def delete_notes_by_space(self, space_id: UUID) -> int:
        """Delete all notes in a space and return count of deleted notes."""
        result = await self._collection.delete_many({"space_id": space_id})
        return result.deleted_count
