from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.counter.models import CounterType
from spacenote.core.modules.field.validators import parse_raw_fields
from spacenote.core.modules.note.models import Note
from spacenote.errors import NotFoundError


class NoteService(Service):
    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("notes")

    async def on_start(self) -> None:
        """Create indexes on startup."""
        # Unique compound index for space_id and number
        await self._collection.create_index([("space_id", 1), ("number", 1)], unique=True)
        # Single index for space_id (for list_notes queries)
        await self._collection.create_index([("space_id", 1)])
        # Single index for created_at (for potential future sorting)
        await self._collection.create_index([("created_at", -1)])

    async def list_notes(self, space_id: UUID) -> list[Note]:
        docs = await self._collection.find({"space_id": space_id}).sort("number", 1).to_list()
        return [Note.model_validate(doc) for doc in docs]

    async def get_note(self, note_id: UUID) -> Note:
        doc = await self._collection.find_one({"_id": note_id})
        if not doc:
            raise NotFoundError(f"Note not found: {note_id}")
        return Note.model_validate(doc)

    async def get_note_by_number(self, space_id: UUID, number: int) -> Note:
        doc = await self._collection.find_one({"space_id": space_id, "number": number})
        if not doc:
            raise NotFoundError(f"Note not found: space_id={space_id}, number={number}")
        return Note.model_validate(doc)

    async def create_note(self, space_id: UUID, author_id: UUID, raw_fields: dict[str, str]) -> Note:
        space = self.core.services.space.get_space(space_id)
        if author_id not in space.members:
            raise NotFoundError(f"User {author_id} is not a member of space {space_id}")

        parsed_fields = parse_raw_fields(space.fields, raw_fields)
        next_number = await self.core.services.counter.get_next_sequence(space_id, CounterType.NOTE)
        res = await self._collection.insert_one(
            Note(
                space_id=space_id,
                number=next_number,
                author_id=author_id,
                fields=parsed_fields,
            ).to_mongo()
        )
        return await self.get_note(res.inserted_id)
