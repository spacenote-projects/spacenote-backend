"""Field validator implementations using ABC pattern."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from spacenote.core.modules.field.models import FieldOption, FieldType, FieldValueType, SpaceField, SpecialValue
from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User
from spacenote.errors import ValidationError


class FieldValidator(ABC):
    """Abstract base class for field validators."""

    def __init__(self, space: Space, members: list[User], current_user_id: UUID | None = None) -> None:
        """Initialize validator with space context.

        Args:
            space: The space this validator is operating on
            members: List of User objects who are members of the space
            current_user_id: The ID of the current logged-in user (optional)
        """
        self.space = space
        self.members = members
        self.current_user_id = current_user_id

    def get_member_by_username(self, username: str) -> User | None:
        """Helper to find member by username."""
        return next((u for u in self.members if u.username == username), None)

    def get_member_by_id(self, user_id: UUID) -> User | None:
        """Helper to find member by ID."""
        return next((u for u in self.members if u.id == user_id), None)

    @abstractmethod
    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        """Parse a raw string value into the field's typed value.

        Args:
            field: The field definition from the space
            raw_value: The raw string value to parse, or None to use default

        Returns:
            The parsed value in the correct type

        Raises:
            ValidationError: If the value cannot be parsed or validated,
                           or if None is passed for a required field without a default
        """

    def validate_field_definition(self, field: SpaceField) -> SpaceField:
        """Validate and transform field definition for storage.

        Template method that validates field name first, then delegates
        to subclass for type-specific validation.

        Args:
            field: The field definition to validate

        Returns:
            The validated and normalized SpaceField

        Raises:
            ValidationError: If the field definition is invalid
        """
        # Always validate field id first
        if not field.id or not field.id.replace("_", "").replace("-", "").isalnum():
            raise ValidationError(f"Invalid field id: {field.id}")

        # Then delegate to subclass for type-specific validation
        return self._validate_type_specific_field_definition(field)

    @abstractmethod
    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        """Validate type-specific field definition.

        Override in subclasses to provide type-specific validation.
        Field name validation is already done by the base class.

        Args:
            field: The field definition to validate

        Returns:
            The validated and normalized SpaceField

        Raises:
            ValidationError: If the field definition is invalid
        """


class StringValidator(FieldValidator):
    """Validator for string fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None
        if raw_value == "" and not field.required:
            return None
        return raw_value

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        return field


class MarkdownValidator(FieldValidator):
    """Validator for markdown fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None
        if raw_value == "" and not field.required:
            return None
        return raw_value

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        return field


class UserValidator(FieldValidator):
    """Validator for user reference fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                # Handle special value $me as default
                if field.default == SpecialValue.ME:
                    if not self.current_user_id:
                        raise ValidationError(f"Cannot use '{SpecialValue.ME}' without a logged-in user context")
                    # Verify current user is a member
                    if not self.get_member_by_id(self.current_user_id):
                        raise ValidationError("Current user is not a member of this space")
                    return self.current_user_id
                # Default is already a UUID object after validation
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        # Handle special value $me
        if raw_value == SpecialValue.ME:
            if not self.current_user_id:
                raise ValidationError(f"Cannot use '{SpecialValue.ME}' without a logged-in user context")
            # Verify current user is a member
            if not self.get_member_by_id(self.current_user_id):
                raise ValidationError("Current user is not a member of this space")
            return self.current_user_id

        # Try to parse as UUID first
        try:
            user_id = UUID(raw_value)
            user = self.get_member_by_id(user_id)
            if not user:
                raise ValidationError(f"User with ID '{user_id}' is not a member of this space")
        except ValueError:
            # Not a UUID, try as username
            user = self.get_member_by_username(raw_value)
            if not user:
                raise ValidationError(f"User '{raw_value}' not found or not a member of this space") from None
            return user.id
        else:
            return user_id

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        # Transform default username or UUID string to UUID object
        if field.default is not None and isinstance(field.default, str):
            # Allow special value $me
            if field.default == SpecialValue.ME:
                return field

            # Store the original string for error messages
            default_str = field.default

            # Try to parse as UUID first
            try:
                user_id = UUID(default_str)
                user = self.get_member_by_id(user_id)
                if not user:
                    raise ValidationError(f"Default user with ID '{user_id}' is not a member of this space")
                # Convert UUID string to UUID object for consistency
                field.default = user_id
            except ValueError:
                # Not a UUID, try as username
                user = self.get_member_by_username(default_str)
                if not user:
                    raise ValidationError(f"Default user '{default_str}' not found or not a member of this space") from None
                field.default = user.id

        return field


class BooleanValidator(FieldValidator):
    """Validator for boolean fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        if raw_value.lower() in ("true", "1", "yes", "on"):
            return True
        if raw_value.lower() in ("false", "0", "no", "off", ""):
            return False
        raise ValidationError(f"Invalid boolean value for field '{field.id}': {raw_value}")

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        if field.default is not None and not isinstance(field.default, bool):
            raise ValidationError("Boolean field default must be boolean")
        return field


class IntValidator(FieldValidator):
    """Validator for integer fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        try:
            int_value = int(raw_value)
        except ValueError as e:
            raise ValidationError(f"Invalid integer value for field '{field.id}': {raw_value}") from e

        self._validate_numeric_range(field, int_value)
        return int_value

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        for opt in (FieldOption.MIN, FieldOption.MAX):
            if opt in field.options:
                val = field.options[opt]
                if not isinstance(val, (int, float)):
                    raise ValidationError(f"{opt} must be numeric")
        return field

    def _validate_numeric_range(self, field: SpaceField, value: int) -> None:
        """Validate numeric value is within min/max range."""
        if FieldOption.MIN in field.options:
            min_val = field.options[FieldOption.MIN]
            if isinstance(min_val, (int, float)) and value < min_val:
                raise ValidationError(f"Value for field '{field.id}' is below minimum: {value} < {min_val}")

        if FieldOption.MAX in field.options:
            max_val = field.options[FieldOption.MAX]
            if isinstance(max_val, (int, float)) and value > max_val:
                raise ValidationError(f"Value for field '{field.id}' is above maximum: {value} > {max_val}")


class FloatValidator(FieldValidator):
    """Validator for float fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        try:
            float_value = float(raw_value)
        except ValueError as e:
            raise ValidationError(f"Invalid float value for field '{field.id}': {raw_value}") from e

        self._validate_numeric_range(field, float_value)
        return float_value

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        for opt in (FieldOption.MIN, FieldOption.MAX):
            if opt in field.options:
                val = field.options[opt]
                if not isinstance(val, (int, float)):
                    raise ValidationError(f"{opt} must be numeric")
        return field

    def _validate_numeric_range(self, field: SpaceField, value: float) -> None:
        """Validate numeric value is within min/max range."""
        if FieldOption.MIN in field.options:
            min_val = field.options[FieldOption.MIN]
            if isinstance(min_val, (int, float)) and value < min_val:
                raise ValidationError(f"Value for field '{field.id}' is below minimum: {value} < {min_val}")

        if FieldOption.MAX in field.options:
            max_val = field.options[FieldOption.MAX]
            if isinstance(max_val, (int, float)) and value > max_val:
                raise ValidationError(f"Value for field '{field.id}' is above maximum: {value} > {max_val}")


class SelectValidator(FieldValidator):
    """Validator for select fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        if FieldOption.VALUES in field.options:
            allowed_values = field.options[FieldOption.VALUES]
            if not isinstance(allowed_values, list):
                raise ValidationError("Invalid field configuration: VALUES must be a list")
            if raw_value not in allowed_values:
                raise ValidationError(
                    f"Invalid choice for field '{field.id}': '{raw_value}'. Allowed values: {', '.join(allowed_values)}"
                )
        return raw_value

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        if FieldOption.VALUES not in field.options:
            raise ValidationError("Select fields must have 'values' option")
        values = field.options[FieldOption.VALUES]
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValidationError("Select 'values' must be a list of strings")

        # Validate VALUE_MAPS if present
        if FieldOption.VALUE_MAPS in field.options:
            value_maps = field.options[FieldOption.VALUE_MAPS]

            # Check it's a dict
            if not isinstance(value_maps, dict):
                raise ValidationError("value_maps must be a dictionary")

            # Check each map
            for map_name, map_data in value_maps.items():
                if not isinstance(map_name, str):
                    raise ValidationError(f"value_maps keys must be strings, got {type(map_name).__name__}")

                if not isinstance(map_data, dict):
                    raise ValidationError(f"value_maps['{map_name}'] must be a dictionary")

                # Check that all VALUES have corresponding entries
                missing_keys = set(values) - set(map_data.keys())
                if missing_keys:
                    raise ValidationError(f"value_maps['{map_name}'] missing entries for: {', '.join(missing_keys)}")

                # Check that no extra keys exist
                extra_keys = set(map_data.keys()) - set(values)
                if extra_keys:
                    raise ValidationError(f"value_maps['{map_name}'] has unknown keys: {', '.join(extra_keys)}")

                # Check all values are strings
                for key, value in map_data.items():
                    if not isinstance(value, str):
                        raise ValidationError(f"value_maps['{map_name}']['{key}'] must be a string, got {type(value).__name__}")

        return field


class TagsValidator(FieldValidator):
    """Validator for tags (multi-value) fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        tags = [tag.strip() for tag in raw_value.split(",") if tag.strip()]
        return list(dict.fromkeys(tags))

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        return field


class DateTimeValidator(FieldValidator):
    """Validator for datetime fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "" and not field.required:
            return None

        # Try common datetime formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
        ]:
            try:
                return datetime.strptime(raw_value, fmt)  # noqa: DTZ007
            except ValueError:
                continue
        raise ValidationError(f"Invalid datetime format for field '{field.id}': {raw_value}")

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        return field


class ImageValidator(FieldValidator):
    """Validator for image attachment fields."""

    def parse_value(self, field: SpaceField, raw_value: str | None) -> FieldValueType:
        if raw_value is None:
            if field.default is not None:
                return field.default
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        if raw_value == "":
            if field.required:
                raise ValidationError(f"Required field '{field.id}' has no value")
            return None

        try:
            attachment_id = UUID(raw_value)
        except ValueError as e:
            raise ValidationError(f"Invalid UUID for field '{field.id}': {raw_value}") from e

        return attachment_id

    def _validate_type_specific_field_definition(self, field: SpaceField) -> SpaceField:
        if FieldOption.PREVIEWS not in field.options:
            raise ValidationError("Image fields must have 'previews' option")

        previews = field.options[FieldOption.PREVIEWS]

        if not isinstance(previews, dict):
            raise ValidationError("Image field 'previews' option must be a dictionary")

        if not previews:
            raise ValidationError("Image field 'previews' option cannot be empty")

        for preview_key, preview_config in previews.items():
            if not isinstance(preview_key, str):
                raise ValidationError(f"Preview key must be a string, got {type(preview_key).__name__}")

            if not isinstance(preview_config, dict):
                raise ValidationError(f"Preview config for '{preview_key}' must be a dictionary")

            if "max_width" not in preview_config:
                raise ValidationError(f"Preview config for '{preview_key}' must have 'max_width'")

            max_width = preview_config["max_width"]
            if not isinstance(max_width, int) or max_width <= 0:
                raise ValidationError(f"Preview 'max_width' for '{preview_key}' must be a positive integer")

        return field


# Map field types to validator classes
_VALIDATOR_CLASSES: dict[FieldType, type[FieldValidator]] = {
    FieldType.STRING: StringValidator,
    FieldType.MARKDOWN: MarkdownValidator,
    FieldType.USER: UserValidator,
    FieldType.BOOLEAN: BooleanValidator,
    FieldType.INT: IntValidator,
    FieldType.FLOAT: FloatValidator,
    FieldType.SELECT: SelectValidator,
    FieldType.TAGS: TagsValidator,
    FieldType.DATETIME: DateTimeValidator,
    FieldType.IMAGE: ImageValidator,
}


def create_validator(
    field_type: FieldType, space: Space, members: list[User], current_user_id: UUID | None = None
) -> FieldValidator:
    """Create a validator instance for a given field type with context.

    Args:
        field_type: The field type to create a validator for
        space: The space this validator will operate on
        members: List of User objects who are members of the space
        current_user_id: The ID of the current logged-in user (optional)

    Returns:
        A validator instance for the field type with context

    Raises:
        ValidationError: If the field type is unknown
    """
    if field_type not in _VALIDATOR_CLASSES:
        raise ValidationError(f"Unknown field type: {field_type}")

    validator_class = _VALIDATOR_CLASSES[field_type]
    return validator_class(space, members, current_user_id)
