from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.comment.models import Comment


class CommentService(Service):
    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("comments")

    async def on_start(self) -> None:
        """Create indexes on startup."""
        await self._collection.create_index([("note_id", 1), ("number", 1)], unique=True)
        await self._collection.create_index([("note_id", 1)])
        await self._collection.create_index([("created_at", 1)])

    async def create_comment(self, note_id: UUID, space_id: UUID, author_id: UUID, content: str) -> Comment:
        """Create a new comment on a note"""
        # Get the next number for this note's comments
        last_comment = await self._collection.find_one({"note_id": note_id}, sort=[("number", -1)])
        next_number = 1 if last_comment is None else last_comment["number"] + 1

        comment = Comment(
            note_id=note_id,
            space_id=space_id,
            author_id=author_id,
            number=next_number,
            content=content,
        )
        await self._collection.insert_one(comment.to_mongo())
        return comment

    async def get_note_comments(self, note_id: UUID) -> list[Comment]:
        """Get all comments for a note, sorted by number"""
        cursor = self._collection.find({"note_id": note_id}).sort("number", 1)
        return await Comment.list_cursor(cursor)
