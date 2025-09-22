from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldValueType, SpaceField
from spacenote.core.modules.field.validators import create_validator
from spacenote.errors import NotFoundError, ValidationError


class FieldService(Service):
    """Service for field validation and management."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    def _parse_field_value(
        self, field: SpaceField, raw_value: str | None, space_id: UUID, current_user_id: UUID | None = None
    ) -> FieldValueType:
        """Parse a raw string value based on field type.

        Args:
            field: The field definition from the space
            raw_value: The raw string value to parse, or None to use default
            space_id: The space ID for this validation
            current_user_id: The ID of the current logged-in user (optional)

        Returns:
            The parsed value in the correct type

        Raises:
            ValidationError: If the value cannot be parsed or validated
        """
        space = self.core.services.space.get_space(space_id)
        members = [self.core.services.user.get_user(uid) for uid in space.members]

        validator = create_validator(field.type, space, members, current_user_id)
        return validator.parse_value(field, raw_value)

    def parse_raw_fields(
        self, space_id: UUID, raw_fields: dict[str, str], current_user_id: UUID | None = None, partial: bool = False
    ) -> dict[str, FieldValueType]:
        """Parse raw string fields into typed values based on space field definitions.

        Args:
            space_id: The space ID for this validation
            raw_fields: Raw string values from the client
            current_user_id: The ID of the current logged-in user (optional)
            partial: If True, only validate provided fields (for updates). If False, validate all fields (for creation)

        Returns:
            Dictionary of parsed field values

        Raises:
            ValidationError: If required fields are missing (when partial=False) or values are invalid
        """
        space = self.core.services.space.get_space(space_id)
        parsed_fields: dict[str, FieldValueType] = {}

        # Check for unknown fields first
        for field_id in raw_fields:
            if space.get_field(field_id) is None:
                raise ValidationError(f"Unknown field: {field_id}")

        if partial:
            # For updates: only parse provided fields
            for field_id, raw_value in raw_fields.items():
                field = space.get_field(field_id)
                if field is not None:
                    parsed_fields[field.id] = self._parse_field_value(field, raw_value, space_id, current_user_id)
        else:
            # For creation: parse all fields (provided and missing)
            for field in space.fields:
                parsed_fields[field.id] = self._parse_field_value(field, raw_fields.get(field.id), space_id, current_user_id)

        return parsed_fields

    async def add_field_to_space(self, space_id: UUID, field: SpaceField) -> None:
        """Add a field to a space with validation.

        Args:
            space_id: The space to add the field to
            field: Field definition to validate, normalize, and add to the space

        Raises:
            ValidationError: If field already exists or is invalid
            NotFoundError: If space not found
        """
        space = self.core.services.space.get_space(space_id)
        if space.get_field(field.id) is not None:
            raise ValidationError(f"Field '{field.id}' already exists in space")

        members = [self.core.services.user.get_user(uid) for uid in space.members]
        validator = create_validator(field.type, space, members, current_user_id=None)
        validated_field = validator.validate_field_definition(field)

        spaces_collection = self.database["spaces"]
        await spaces_collection.update_one({"_id": space_id}, {"$push": {"fields": validated_field.model_dump()}})
        await self.core.services.space.update_space_cache(space_id)

    async def remove_field_from_space(self, space_id: UUID, field_id: str) -> None:
        """Remove a field from a space.

        Args:
            space_id: The space to remove the field from
            field_id: The id of the field to remove

        Raises:
            ValidationError: If field is in use or doesn't exist
            NotFoundError: If space not found
        """
        space = self.core.services.space.get_space(space_id)
        field = space.get_field(field_id)
        if field is None:
            raise NotFoundError(f"Field '{field_id}' not found in space")

        # Check if field is used in any notes
        notes_collection = self.database["notes"]
        note_count = await notes_collection.count_documents({"space_id": space_id, f"fields.{field_id}": {"$exists": True}})
        if note_count > 0:
            raise ValidationError(f"Cannot remove field '{field_id}' - it is used in {note_count} note(s)")

        spaces_collection = self.database["spaces"]
        await spaces_collection.update_one({"_id": space_id}, {"$pull": {"fields": {"id": field_id}}})
        await self.core.services.space.update_space_cache(space_id)
