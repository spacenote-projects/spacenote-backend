from typing import Any
from uuid import UUID

import structlog
from pymongo.asynchronous.database import AsyncDatabase

from spacenote import utils
from spacenote.core.core import Service
from spacenote.core.modules.note.models import NOTE_SYSTEM_FIELDS
from spacenote.core.modules.space.models import Space
from spacenote.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class SpaceService(Service):
    """Service for managing spaces with in-memory caching."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("spaces")
        self._spaces: dict[UUID, Space] = {}

    async def on_start(self) -> None:
        await self._collection.create_index([("slug", 1)], unique=True)
        await self.update_all_spaces_cache()
        logger.debug("space_service_started", space_count=len(self._spaces))

    async def update_all_spaces_cache(self) -> None:
        """Reload all spaces cache from database."""
        spaces = await Space.list_cursor(self._collection.find())
        self._spaces = {space.id: space for space in spaces}

    async def update_space_cache(self, space_id: UUID) -> Space:
        """Reload a specific space cache from database."""
        space = await self._collection.find_one({"_id": space_id})
        if space is None:
            raise NotFoundError(f"Space '{space_id}' not found")
        self._spaces[space_id] = Space.model_validate(space)
        return self._spaces[space_id]

    def get_space(self, space_id: UUID) -> Space:
        """Get a space by ID."""
        if space_id not in self._spaces:
            raise NotFoundError(f"Space '{space_id}' not found")
        return self._spaces[space_id]

    def get_space_by_slug(self, slug: str) -> Space:
        """Get a space by slug."""
        for space in self._spaces.values():
            if space.slug == slug:
                return space
        raise NotFoundError(f"Space with slug '{slug}' not found")

    def get_spaces_by_member(self, member: UUID) -> list[Space]:
        """Get all spaces where the user is a member."""
        return [space for space in self._spaces.values() if member in space.members]

    def is_user_member_of_any_space(self, user_id: UUID) -> bool:
        """Check if a user is a member of any space."""
        return any(user_id in space.members for space in self._spaces.values())

    def has_slug(self, slug: str) -> bool:
        """Check if a space exists by slug."""
        return any(space.slug == slug for space in self._spaces.values())

    async def create_space(self, slug: str, title: str, description: str, member: UUID) -> Space:
        """Create a new space with validation."""
        if not self.core.services.user.has_user(member):
            raise ValidationError(f"User '{member}' does not exist")
        if not utils.is_slug(slug):
            raise ValidationError(f"Invalid slug format: '{slug}'")
        if self.has_slug(slug):
            raise ValidationError(f"Space with slug '{slug}' already exists")

        res = await self._collection.insert_one(
            Space(slug=slug, title=title, description=description, members=[member]).to_mongo()
        )
        return await self.update_space_cache(res.inserted_id)

    async def add_member(self, space_id: UUID, user_id: UUID) -> Space:
        """Add a member to a space."""
        space = self.get_space(space_id)

        if not self.core.services.user.has_user(user_id):
            raise NotFoundError(f"User '{user_id}' not found")

        if user_id in space.members:
            raise ValidationError("User is already a member of this space")

        await self._collection.update_one({"_id": space_id}, {"$push": {"members": user_id}})
        return await self.update_space_cache(space_id)

    async def remove_member(self, space_id: UUID, user_id: UUID) -> None:
        """Remove a member from a space."""
        space = self.get_space(space_id)

        if user_id not in space.members:
            raise ValidationError("User is not a member of this space")

        if len(space.members) == 1:
            raise ValidationError("Cannot remove the last member from a space")

        await self._collection.update_one({"_id": space_id}, {"$pull": {"members": user_id}})
        await self.update_space_cache(space_id)

    async def update_template(self, space_id: UUID, template_name: str, template_content: str | None) -> Space:
        """Update a specific template for a space."""
        self.get_space(space_id)

        if template_name not in ["note_detail", "note_list"]:
            raise ValidationError(f"Invalid template name: '{template_name}'. Must be 'note_detail' or 'note_list'")

        await self._collection.update_one({"_id": space_id}, {"$set": {f"templates.{template_name}": template_content}})

        return await self.update_space_cache(space_id)

    async def update_list_fields(self, space_id: UUID, field_ids: list[str]) -> Space:
        """Update the list_fields for a space.

        Allows both space-defined fields and system fields (number, created_at, author).
        """
        space = self.get_space(space_id)

        for field_id in field_ids:
            if field_id not in NOTE_SYSTEM_FIELDS and not space.get_field(field_id):
                raise ValidationError(f"Field '{field_id}' does not exist in space")

        await self._collection.update_one({"_id": space_id}, {"$set": {"list_fields": field_ids}})
        return await self.update_space_cache(space_id)

    async def update_hidden_create_fields(self, space_id: UUID, field_ids: list[str]) -> Space:
        """Update the hidden_create_fields for a space."""
        space = self.get_space(space_id)

        for field_id in field_ids:
            if not space.get_field(field_id):
                raise ValidationError(f"Field '{field_id}' does not exist in space")

        await self._collection.update_one({"_id": space_id}, {"$set": {"hidden_create_fields": field_ids}})
        return await self.update_space_cache(space_id)

    async def update_comment_editable_fields(self, space_id: UUID, field_ids: list[str]) -> Space:
        """Update the comment_editable_fields for a space."""
        space = self.get_space(space_id)

        for field_id in field_ids:
            if not space.get_field(field_id):
                raise ValidationError(f"Field '{field_id}' does not exist in space")

        await self._collection.update_one({"_id": space_id}, {"$set": {"comment_editable_fields": field_ids}})
        return await self.update_space_cache(space_id)

    async def update_default_filter(self, space_id: UUID, filter_id: str | None) -> Space:
        """Update the default_filter for a space."""
        space = self.get_space(space_id)

        if filter_id is not None and not space.get_filter(filter_id):
            raise ValidationError(f"Filter '{filter_id}' does not exist in space")

        await self._collection.update_one({"_id": space_id}, {"$set": {"default_filter": filter_id}})
        return await self.update_space_cache(space_id)

    async def update_title(self, space_id: UUID, title: str) -> Space:
        """Update the title of a space."""
        self.get_space(space_id)

        if not title.strip():
            raise ValidationError("Title cannot be empty")

        await self._collection.update_one({"_id": space_id}, {"$set": {"title": title}})
        return await self.update_space_cache(space_id)

    async def update_description(self, space_id: UUID, description: str) -> Space:
        """Update the description of a space."""
        self.get_space(space_id)

        await self._collection.update_one({"_id": space_id}, {"$set": {"description": description}})
        return await self.update_space_cache(space_id)

    async def update_slug(self, space_id: UUID, new_slug: str) -> Space:
        """Update the slug of a space."""
        space = self.get_space(space_id)

        if not utils.is_slug(new_slug):
            raise ValidationError(f"Invalid slug format: '{new_slug}'")

        if space.slug == new_slug:
            return space

        if self.has_slug(new_slug):
            raise ValidationError(f"Space with slug '{new_slug}' already exists")

        await self._collection.update_one({"_id": space_id}, {"$set": {"slug": new_slug}})
        return await self.update_space_cache(space_id)

    async def delete_space(self, space_id: UUID) -> None:
        """Delete a space and remove from cache."""
        result = await self._collection.delete_one({"_id": space_id})
        if result.deleted_count == 0:
            raise NotFoundError(f"Space '{space_id}' not found")

        if space_id in self._spaces:
            del self._spaces[space_id]
