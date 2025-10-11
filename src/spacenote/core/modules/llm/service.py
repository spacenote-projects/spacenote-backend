import time
from typing import Any, Protocol
from uuid import UUID

import litellm
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.llm.models import LLMLog, LLMOperationType, ParsedApiCall
from spacenote.core.modules.llm.prompts import build_intent_classification_prompt
from spacenote.core.modules.llm.utils import parse_line_based_response
from spacenote.core.modules.space.models import Space
from spacenote.core.pagination import PaginationResult
from spacenote.errors import ValidationError


class LLMUsage(Protocol):
    """Protocol for LLM usage statistics from litellm response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMService(Service):
    """LLM service for parsing natural language into API calls"""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)
        self._collection = database.get_collection("llm_logs")

    async def on_start(self) -> None:
        """Create indexes for LLM logs."""
        await self._collection.create_index([("user_id", 1)])
        await self._collection.create_index([("created_at", -1)])
        await self._collection.create_index([("space_id", 1)])

    async def get_logs(self, limit: int = 50, offset: int = 0) -> PaginationResult[LLMLog]:
        """Get paginated LLM logs."""
        total = await self._collection.count_documents({})

        cursor = self._collection.find({}).sort("created_at", -1).skip(offset).limit(limit)
        items = await LLMLog.list_cursor(cursor)

        return PaginationResult(items=items, total=total, limit=limit, offset=offset)

    def _build_api_call(self, operation_type: str, space_slug: str, parsed_data: dict[str, str]) -> ParsedApiCall:
        """
        Build ParsedApiCall from parsed LLM response.

        Args:
            operation_type: Type of operation (create_note, update_note, create_comment)
            space_slug: Space identifier
            parsed_data: Raw parsed data from LLM response

        Returns:
            ParsedApiCall with method, path, and body
        """
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

    async def parse_intent(self, text: str, available_spaces: list[Space], user_id: UUID) -> ParsedApiCall:
        """
        Parse natural language into ready-to-use API call.

        Uses line-based format instead of JSON for LLM responses because it's more
        resilient to LLM errors (malformed JSON breaks completely, line-based can
        skip bad lines and recover).

        Args:
            text: User's natural language input
            available_spaces: List of Space objects user has access to
            user_id: User ID for logging

        Returns:
            ParsedApiCall with method, path, and body
        """
        start_time = time.time()
        system_prompt = build_intent_classification_prompt(available_spaces)
        llm_response_content = None
        parsed_data = None
        space_id = None
        usage_tokens = None
        operation_type_enum = None

        try:
            if not self.core.config.llm_api_key:
                raise ValidationError("LLM API key not configured")  # noqa: TRY301

            if not available_spaces:
                raise ValidationError("No spaces available")  # noqa: TRY301

            response = litellm.completion(
                model=self.core.config.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                api_key=self.core.config.llm_api_key,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            usage = getattr(response, "usage", None)
            if usage:
                usage_tokens = (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)

            llm_response_content = response.choices[0].message.content
            if not llm_response_content:
                raise ValidationError("LLM returned empty response")  # noqa: TRY301

            parsed_data = parse_line_based_response(llm_response_content)

            operation_type = parsed_data.get("operation_type")
            if not operation_type:
                raise ValidationError("Missing operation_type in LLM response")  # noqa: TRY301

            operation_type_enum = LLMOperationType(operation_type)

            space_slug = parsed_data.get("space_slug")
            if not space_slug:
                raise ValidationError("Missing space_slug in LLM response")  # noqa: TRY301

            if space_slug not in [space.slug for space in available_spaces]:
                raise ValidationError(f"Space '{space_slug}' not found")  # noqa: TRY301

            space = next(s for s in available_spaces if s.slug == space_slug)
            space_id = space.id

            result = self._build_api_call(operation_type, space_slug, parsed_data)

            log = LLMLog(
                user_input=text,
                llm_response=llm_response_content,
                parsed_response=parsed_data,
                user_id=user_id,
                operation_type=operation_type_enum,
                space_id=space_id,
                system_prompt=system_prompt,
                context_data={"available_space_ids": [str(s.id) for s in available_spaces]},
                model=self.core.config.llm_model,
                prompt_tokens=usage_tokens[0] if usage_tokens else None,
                completion_tokens=usage_tokens[1] if usage_tokens else None,
                total_tokens=usage_tokens[2] if usage_tokens else None,
                error_message=None,
                duration_ms=duration_ms,
            )
            await self._collection.insert_one(log.to_mongo())

            return result  # noqa: TRY300

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log = LLMLog(
                user_input=text,
                llm_response=llm_response_content,
                parsed_response=parsed_data,
                user_id=user_id,
                operation_type=operation_type_enum,
                space_id=space_id,
                system_prompt=system_prompt,
                context_data={"available_space_ids": [str(s.id) for s in available_spaces]},
                model=self.core.config.llm_model,
                prompt_tokens=usage_tokens[0] if usage_tokens else None,
                completion_tokens=usage_tokens[1] if usage_tokens else None,
                total_tokens=usage_tokens[2] if usage_tokens else None,
                error_message=str(e),
                duration_ms=duration_ms,
            )
            await self._collection.insert_one(log.to_mongo())
            raise
