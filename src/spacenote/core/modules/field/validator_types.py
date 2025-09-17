"""Field validator implementations using ABC pattern."""

from abc import ABC, abstractmethod
from datetime import datetime

from spacenote.core.modules.field.models import FieldOption, FieldType, FieldValueType, SpaceField
from spacenote.errors import ValidationError


class FieldValidator(ABC):
    """Abstract base class for field validators."""

    @abstractmethod
    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        """Parse a raw string value into the field's typed value.

        Args:
            field: The field definition from the space
            raw_value: The raw string value to parse

        Returns:
            The parsed value in the correct type

        Raises:
            ValidationError: If the value cannot be parsed or validated
        """

    @abstractmethod
    def validate_definition(self, field: SpaceField) -> SpaceField:
        """Validate and transform field definition for storage.

        May transform values (e.g., username → UUID for USER fields).

        Args:
            field: The field definition to validate

        Returns:
            The validated and normalized SpaceField

        Raises:
            ValidationError: If the field definition is invalid
        """


class StringValidator(FieldValidator):
    """Validator for string fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None
        return raw_value

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")
        return field


class MarkdownValidator(FieldValidator):
    """Validator for markdown fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None
        return raw_value

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")
        return field


class UserValidator(FieldValidator):
    """Validator for user reference fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None
        return raw_value

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")
        # TODO: In the future, transform username to UUID here if needed
        return field


class BooleanValidator(FieldValidator):
    """Validator for boolean fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None

        if raw_value.lower() in ("true", "1", "yes", "on"):
            return True
        if raw_value.lower() in ("false", "0", "no", "off", ""):
            return False
        raise ValidationError(f"Invalid boolean value for field '{field.name}': {raw_value}")

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")

        if field.default is not None and not isinstance(field.default, bool):
            raise ValidationError("Boolean field default must be boolean")
        return field


class IntValidator(FieldValidator):
    """Validator for integer fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None

        try:
            int_value = int(raw_value)
        except ValueError as e:
            raise ValidationError(f"Invalid integer value for field '{field.name}': {raw_value}") from e

        self._validate_numeric_range(field, int_value)
        return int_value

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")

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
                raise ValidationError(f"Value for field '{field.name}' is below minimum: {value} < {min_val}")

        if FieldOption.MAX in field.options:
            max_val = field.options[FieldOption.MAX]
            if isinstance(max_val, (int, float)) and value > max_val:
                raise ValidationError(f"Value for field '{field.name}' is above maximum: {value} > {max_val}")


class FloatValidator(FieldValidator):
    """Validator for float fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None

        try:
            float_value = float(raw_value)
        except ValueError as e:
            raise ValidationError(f"Invalid float value for field '{field.name}': {raw_value}") from e

        self._validate_numeric_range(field, float_value)
        return float_value

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")

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
                raise ValidationError(f"Value for field '{field.name}' is below minimum: {value} < {min_val}")

        if FieldOption.MAX in field.options:
            max_val = field.options[FieldOption.MAX]
            if isinstance(max_val, (int, float)) and value > max_val:
                raise ValidationError(f"Value for field '{field.name}' is above maximum: {value} > {max_val}")


class StringChoiceValidator(FieldValidator):
    """Validator for string choice (single select) fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None

        if FieldOption.VALUES in field.options:
            allowed_values = field.options[FieldOption.VALUES]
            if not isinstance(allowed_values, list):
                raise ValidationError("Invalid field configuration: VALUES must be a list")
            if raw_value not in allowed_values:
                raise ValidationError(
                    f"Invalid choice for field '{field.name}': '{raw_value}'. Allowed values: {', '.join(allowed_values)}"
                )
        return raw_value

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")

        if FieldOption.VALUES not in field.options:
            raise ValidationError("String choice fields must have 'values' option")
        values = field.options[FieldOption.VALUES]
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValidationError("String choice 'values' must be a list of strings")
        return field


class TagsValidator(FieldValidator):
    """Validator for tags (multi-value) fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
        if raw_value == "" and not field.required:
            return None

        tags = [tag.strip() for tag in raw_value.split(",") if tag.strip()]

        if FieldOption.VALUES in field.options:
            allowed_values = field.options[FieldOption.VALUES]
            if not isinstance(allowed_values, list):
                raise ValidationError("Invalid field configuration: VALUES must be a list")
            invalid_tags = [tag for tag in tags if tag not in allowed_values]
            if invalid_tags:
                raise ValidationError(
                    f"Invalid tags for field '{field.name}': {', '.join(invalid_tags)}. "
                    f"Allowed values: {', '.join(allowed_values)}"
                )
        return tags

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")
        return field


class DateTimeValidator(FieldValidator):
    """Validator for datetime fields."""

    def parse_value(self, field: SpaceField, raw_value: str) -> FieldValueType:
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
        raise ValidationError(f"Invalid datetime format for field '{field.name}': {raw_value}")

    def validate_definition(self, field: SpaceField) -> SpaceField:
        if not field.name or not field.name.replace("_", "").isalnum():
            raise ValidationError(f"Invalid field name: {field.name}")
        return field


# Validator registry - singleton instances
_VALIDATORS: dict[FieldType, FieldValidator] = {
    FieldType.STRING: StringValidator(),
    FieldType.MARKDOWN: MarkdownValidator(),
    FieldType.USER: UserValidator(),
    FieldType.BOOLEAN: BooleanValidator(),
    FieldType.INT: IntValidator(),
    FieldType.FLOAT: FloatValidator(),
    FieldType.STRING_CHOICE: StringChoiceValidator(),
    FieldType.TAGS: TagsValidator(),
    FieldType.DATETIME: DateTimeValidator(),
}


def get_validator(field_type: FieldType) -> FieldValidator:
    """Get the validator for a given field type.

    Args:
        field_type: The field type to get a validator for

    Returns:
        The validator instance for the field type

    Raises:
        ValidationError: If the field type is unknown
    """
    if field_type not in _VALIDATORS:
        raise ValidationError(f"Unknown field type: {field_type}")
    return _VALIDATORS[field_type]
