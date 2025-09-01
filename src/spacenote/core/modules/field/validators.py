from spacenote.core.modules.field.models import FieldOption, FieldType, SpaceField
from spacenote.errors import ValidationError


def validate_space_field(field: SpaceField) -> SpaceField:
    """Validate field definition.

    Returns a validated SpaceField.
    """
    # Validate field name format
    if not field.name or not field.name.replace("_", "").isalnum():
        raise ValidationError(f"Invalid field name: {field.name}")

    # Type-specific validation
    match field.type:
        case FieldType.STRING_CHOICE:
            if FieldOption.VALUES not in field.options:
                raise ValidationError("String choice fields must have 'values' option")
            values = field.options[FieldOption.VALUES]
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ValidationError("String choice 'values' must be a list of strings")

        case FieldType.INT | FieldType.FLOAT:
            for opt in (FieldOption.MIN, FieldOption.MAX):
                if opt in field.options:
                    val = field.options[opt]
                    if not isinstance(val, (int, float)):
                        raise ValidationError(f"{opt} must be numeric")

        case FieldType.BOOLEAN:
            if field.default is not None and not isinstance(field.default, bool):
                raise ValidationError("Boolean field default must be boolean")

    return field
