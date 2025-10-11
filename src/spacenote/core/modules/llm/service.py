import litellm

from spacenote.core.core import Service
from spacenote.core.modules.llm.models import ParsedApiCall
from spacenote.core.modules.llm.prompts import build_intent_classification_prompt
from spacenote.core.modules.llm.utils import parse_line_based_response
from spacenote.core.modules.space.models import Space
from spacenote.errors import ValidationError


class LLMService(Service):
    """LLM service for parsing natural language into API calls"""

    def parse_intent(self, text: str, available_spaces: list[Space]) -> ParsedApiCall:
        """
        Parse natural language into ready-to-use API call.

        Args:
            text: User's natural language input
            available_spaces: List of Space objects user has access to

        Returns:
            ParsedApiCall with method, path, and body
        """
        if not self.core.config.llm_api_key:
            raise ValidationError("LLM API key not configured")

        if not available_spaces:
            raise ValidationError("No spaces available")

        system_prompt = build_intent_classification_prompt(available_spaces)

        response = litellm.completion(
            model=self.core.config.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            api_key=self.core.config.llm_api_key,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValidationError("LLM returned empty response")

        parsed_data = parse_line_based_response(content)

        operation_type = parsed_data.get("operation_type")
        if not operation_type:
            raise ValidationError("Missing operation_type in LLM response")

        space_slug = parsed_data.get("space_slug")
        if not space_slug:
            raise ValidationError("Missing space_slug in LLM response")

        if space_slug not in [space.slug for space in available_spaces]:
            raise ValidationError(f"Space '{space_slug}' not found")

        if operation_type == "create_note":
            fields = {k: v for k, v in parsed_data.items() if k not in ("operation_type", "space_slug")}
            return ParsedApiCall(
                method="POST",
                path=f"/api/v1/spaces/{space_slug}/notes",
                body={"raw_fields": fields},
            )

        if operation_type == "update_note":
            note_number_str = parsed_data.get("note_number")
            if not note_number_str:
                raise ValidationError("Missing note_number for update_note operation")
            try:
                note_number = int(note_number_str)
            except ValueError as e:
                raise ValidationError(f"Invalid note_number: {note_number_str}") from e

            fields = {k: v for k, v in parsed_data.items() if k not in ("operation_type", "space_slug", "note_number")}
            return ParsedApiCall(
                method="PATCH",
                path=f"/api/v1/spaces/{space_slug}/notes/{note_number}",
                body={"raw_fields": fields},
            )

        if operation_type == "create_comment":
            note_number_str = parsed_data.get("note_number")
            if not note_number_str:
                raise ValidationError("Missing note_number for create_comment operation")
            try:
                note_number = int(note_number_str)
            except ValueError as e:
                raise ValidationError(f"Invalid note_number: {note_number_str}") from e

            content_text = parsed_data.get("content")
            if not content_text:
                raise ValidationError("Missing content for create_comment operation")

            return ParsedApiCall(
                method="POST",
                path=f"/api/v1/spaces/{space_slug}/notes/{note_number}/comments",
                body={"content": content_text},
            )

        raise ValidationError(f"Unknown operation type: {operation_type}")
