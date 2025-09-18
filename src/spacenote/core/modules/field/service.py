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

        validator = create_validator(field.type, space, members)
        return validator.validate_field_definition(field)

    def _parse_field_value(self, field: SpaceField, raw_value: str, space_id: UUID) -> FieldValueType:
        """Parse a raw string value based on field type.

        Args:
            field: The field definition from the space
            raw_value: The raw string value to parse
            space_id: The space ID for this validation

        Returns:
            The parsed value in the correct type

        Raises:
            ValidationError: If the value cannot be parsed or validated
        """
        space = self.core.services.space.get_space(space_id)
        members = [self.core.services.user.get_user(uid) for uid in space.members]

        validator = create_validator(field.type, space, members)
        return validator.parse_value(field, raw_value)

    def parse_raw_fields(self, space_id: UUID, raw_fields: dict[str, str]) -> dict[str, FieldValueType]:
        """Parse raw string fields into typed values based on space field definitions.

        Args:
            space_id: The space ID for this validation
            raw_fields: Raw string values from the client

        Returns:
            Dictionary of parsed field values

        Raises:
            ValidationError: If required fields are missing or values are invalid
        """
        space = self.core.services.space.get_space(space_id)
        space_fields = space.fields
        parsed_fields: dict[str, FieldValueType] = {}

        # Create a map for quick lookup
        field_map = {field.name: field for field in space_fields}

        # Check for required fields
        for field in space_fields:
            if field.required and field.name not in raw_fields:
                raise ValidationError(f"Required field missing: {field.name}")

        # Parse each provided field
        for field_name, raw_value in raw_fields.items():
            if field_name not in field_map:
                raise ValidationError(f"Unknown field: {field_name}")

            field = field_map[field_name]
            parsed_value = self._parse_field_value(field, raw_value, space_id)

            # Only add non-null values
            if parsed_value is not None:
                parsed_fields[field_name] = parsed_value

        # Add default values for missing optional fields
        for field in space_fields:
            if field.name not in parsed_fields and field.default is not None:
                parsed_fields[field.name] = field.default

        return parsed_fields
