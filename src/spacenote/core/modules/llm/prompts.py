from spacenote.core.modules.space.models import Space


def build_intent_classification_prompt(available_spaces: list[Space]) -> str:
    """Build system prompt for classifying user intent into API operations."""
    spaces_info = "\n".join([f"- {space.slug}: {space.title} - {space.description}" for space in available_spaces])

    return f"""You are an assistant that classifies user intent into API operations.

Available spaces:
{spaces_info}

Supported operations:
- create_note: Create a new note in a space
- update_note: Update an existing note's fields
- create_comment: Add a comment to an existing note

Analyze the user's message and determine:
1. Which space they're referring to (use the slug)
2. What operation they want to perform

Respond with JSON containing space_slug and operation_type."""
