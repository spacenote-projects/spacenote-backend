from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.comment.models import Comment
from spacenote.core.pagination import PaginationResult
from spacenote.utils import now


class CommentService(Service):
    """Manages comments on notes with auto-increment numbering."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("comments")

    async def on_start(self) -> None:
        """Create indexes for note/number lookup."""
        await self._collection.create_index([("note_id", 1), ("number", 1)], unique=True)
        await self._collection.create_index([("note_id", 1)])
        await self._collection.create_index([("created_at", 1)])

    async def create_comment(self, note_id: UUID, space_id: UUID, author_id: UUID, content: str) -> Comment:
        """Create comment with auto-increment number per note."""
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

        # Update note's commented_at and activity_at timestamps
        timestamp = now()
        notes_collection = self.database.get_collection("notes")
        await notes_collection.update_one({"_id": note_id}, {"$set": {"commented_at": timestamp, "activity_at": timestamp}})

        return comment

    async def get_note_comments(self, note_id: UUID, limit: int = 50, offset: int = 0) -> PaginationResult[Comment]:
        """Get paginated comments for note, sorted by number descending."""
        query = {"note_id": note_id}

        # Get total count
        total = await self._collection.count_documents(query)

        # Get paginated items
        cursor = self._collection.find(query).sort("number", -1).skip(offset).limit(limit)
        items = await Comment.list_cursor(cursor)

        return PaginationResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def delete_comments_by_space(self, space_id: UUID) -> int:
        """Delete all comments in a space and return count of deleted comments."""
        result = await self._collection.delete_many({"space_id": space_id})
        return result.deleted_count
