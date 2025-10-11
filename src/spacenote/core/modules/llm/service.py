from uuid import UUID

import litellm

from spacenote.core.core import Service
from spacenote.core.modules.llm.models import IntentClassification, ParsedApiCall
from spacenote.core.modules.llm.prompts import build_intent_classification_prompt
from spacenote.core.modules.space.models import Space
from spacenote.errors import ValidationError


class LLMService(Service):
    """LLM service for parsing natural language into API calls"""

    def parse_intent(self, text: str, available_spaces: list[Space], _current_user_id: UUID) -> ParsedApiCall:
        """
        Parse natural language into ready-to-use API call.

        Args:
            text: User's natural language input
            available_spaces: List of Space objects user has access to
            _current_user_id: Current user UUID (for context, currently unused)

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
            response_format=IntentClassification,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValidationError("LLM returned empty response")

        classification = IntentClassification.model_validate_json(content)

        if classification.space_slug not in [space.slug for space in available_spaces]:
            raise ValidationError(f"Space '{classification.space_slug}' not found")

        if classification.operation_type == "create_note":
            return ParsedApiCall(
                method="POST",
                path=f"/api/v1/spaces/{classification.space_slug}/notes",
                body={"raw_fields": {"title": "New task from chat"}},
            )
        if classification.operation_type == "update_note":
            return ParsedApiCall(
                method="PATCH",
                path=f"/api/v1/spaces/{classification.space_slug}/notes/1",
                body={"raw_fields": {"status": "in_progress"}},
            )
        return ParsedApiCall(
            method="POST",
            path=f"/api/v1/spaces/{classification.space_slug}/notes/1/comments",
            body={"content": "Comment from chat"},
        )
