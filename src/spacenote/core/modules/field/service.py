from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.field.models import FieldValueType, SpaceField
from spacenote.core.modules.field.validators import create_validator
from spacenote.errors import ValidationError


class FieldService(Service):
    """Service for field validation and management."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    def validate_field_definition(self, space_id: UUID, field: SpaceField) -> SpaceField:
        """Validate field definition.

        Args:
            space_id: The space ID for this validation
            field: The field definition to validate

        Returns:
            A validated SpaceField.
        """
        space = self.core.services.space.get_space(space_id)
        members = [self.core.services.user.get_user(uid) for uid in space.members]

        validator = create_validator(field.type, space, members, current_user_id=None)
        return validator.validate_field_definition(field)

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
        self, space_id: UUID, raw_fields: dict[str, str], current_user_id: UUID | None = None
    ) -> dict[str, FieldValueType]:
        """Parse raw string fields into typed values based on space field definitions.

        Args:
            space_id: The space ID for this validation
            raw_fields: Raw string values from the client
            current_user_id: The ID of the current logged-in user (optional)

        Returns:
            Dictionary of parsed field values

        Raises:
            ValidationError: If required fields are missing or values are invalid
        """
        space = self.core.services.space.get_space(space_id)
        parsed_fields: dict[str, FieldValueType] = {}

        # Check for unknown fields first
        for field_name in raw_fields:
            if space.get_field(field_name) is None:
                raise ValidationError(f"Unknown field: {field_name}")

        # Parse each field (provided and missing)
        for field in space.fields:
            parsed_fields[field.name] = self._parse_field_value(field, raw_fields.get(field.name), space_id, current_user_id)

        return parsed_fields
