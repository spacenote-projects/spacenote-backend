from spacenote.core.modules.field.models import FieldOption
from spacenote.core.modules.space.models import Space


def _format_field_schema(space: Space) -> str:
    """Format field schema for a space."""
    if not space.fields:
        return "  No custom fields defined"

    field_lines = []
    for field in space.fields:
        field_info = f"  - {field.id} ({field.type})"
        if field.required:
            field_info += " [required]"
        if field.default is not None:
            field_info += f" [default: {field.default}]"
        if FieldOption.VALUES in field.options:
            values = field.options[FieldOption.VALUES]
            if isinstance(values, list):
                field_info += f"\n    Allowed values: {', '.join(values)}"
        if FieldOption.MIN in field.options or FieldOption.MAX in field.options:
            min_val = field.options.get(FieldOption.MIN)
            max_val = field.options.get(FieldOption.MAX)
            range_info = []
            if min_val is not None:
                range_info.append(f"min={min_val}")
            if max_val is not None:
                range_info.append(f"max={max_val}")
            field_info += f" [{', '.join(range_info)}]"
        field_lines.append(field_info)

    return "\n".join(field_lines)


def build_intent_classification_prompt(available_spaces: list[Space]) -> str:
    """Build system prompt for classifying user intent and extracting parameters."""
    spaces_info = []
    for space in available_spaces:
        field_schema = _format_field_schema(space)
        space_info = f"Space: {space.slug}\n  Title: {space.title}\n  Description: {space.description}\n  Fields:\n{field_schema}"
        spaces_info.append(space_info)

    spaces_block = "\n\n".join(spaces_info)

    return f"""You are an assistant that parses user intent into structured API operations.

AVAILABLE SPACES:
{spaces_block}

SUPPORTED OPERATIONS:

1. create_note - Create a new note in a space
   Required: operation_type, space_slug, field values

   Example response:
   operation_type: create_note
   space_slug: my-tasks
   title: Buy milk
   tags: shopping, food

2. update_note - Update an existing note's fields
   Required: operation_type, space_slug, note_number, field values to update

   Example response:
   operation_type: update_note
   space_slug: my-tasks
   note_number: 5
   status: completed

3. create_comment - Add a comment to a note
   Required: operation_type, space_slug, note_number, content

   Example response:
   operation_type: create_comment
   space_slug: my-tasks
   note_number: 3
   content: This is completed

RESPONSE FORMAT:
- Each line: key: value
- First line: operation_type (create_note, update_note, or create_comment)
- Second line: space_slug
- For update_note/create_comment: third line is note_number
- Remaining lines: field names and values (for create_note/update_note) or content (for create_comment)
- All values as strings

EXTRACTION RULES:

1. Identify the target space from context (use slug)
2. Determine the operation type
3. Extract all relevant parameters:
   - For create_note: extract field values from user text
   - For update_note: identify note number and fields to update
   - For create_comment: identify note number and comment text

4. Extract field values as strings (all values must be strings):
   - For select fields: use exact values from "Allowed values" list in space schema
   - For boolean fields: use "true" or "false" as strings
   - For user fields: can use "$me" for current user
   - For numbers: extract as strings (e.g., "5", "3.14")
   - For dates: extract as strings (e.g., "2024-01-15")
   - Map natural language to appropriate allowed values based on space schema

5. Only include fields mentioned by the user (except required fields for create_note)

Respond with line-based format as shown in examples above."""  # noqa: S608
