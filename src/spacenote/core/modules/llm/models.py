from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel
from spacenote.utils import now


class LLMOperationType(str, Enum):
    """LLM operation types."""

    PARSE_INTENT = "parse_intent"


class ParsedApiCall(BaseModel):
    """Parsed API call from natural language input."""

    method: str = Field(..., description="HTTP method (POST, PATCH, GET)")
    path: str = Field(..., description="API endpoint path")
    body: dict[str, Any] | None = Field(None, description="Request body")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "method": "POST",
                    "path": "/api/v1/spaces/workspace/notes",
                    "body": {"raw_fields": {"title": "Meeting tomorrow"}},
                }
            ]
        }
    }


class CreateNoteIntent(BaseModel):
    """
    Intent to create a new note in a space.

    NOTE: This model serves as schema documentation and reference.
    It is NOT used for parsing LLM responses (we use line-based parsing instead).
    See utils.parse_line_based_response() for the actual parsing logic.
    """

    operation_type: Literal["create_note"] = "create_note"
    space_slug: str = Field(..., description="Slug of the space to create note in")
    fields: dict[str, str] = Field(..., description="Field values for the new note as strings")


class UpdateNoteIntent(BaseModel):
    """
    Intent to update an existing note.

    NOTE: This model serves as schema documentation and reference.
    It is NOT used for parsing LLM responses (we use line-based parsing instead).
    See utils.parse_line_based_response() for the actual parsing logic.
    """

    operation_type: Literal["update_note"] = "update_note"
    space_slug: str = Field(..., description="Slug of the space containing the note")
    note_number: int = Field(..., description="Note number to update")
    fields: dict[str, str] = Field(..., description="Field values to update as strings")


class CreateCommentIntent(BaseModel):
    """
    Intent to create a comment on a note.

    NOTE: This model serves as schema documentation and reference.
    It is NOT used for parsing LLM responses (we use line-based parsing instead).
    See utils.parse_line_based_response() for the actual parsing logic.
    """

    operation_type: Literal["create_comment"] = "create_comment"
    space_slug: str = Field(..., description="Slug of the space containing the note")
    note_number: int = Field(..., description="Note number to comment on")
    content: str = Field(..., description="Comment text content")


class LLMLog(MongoModel):
    """Log of LLM API interaction."""

    user_id: UUID
    user_input: str
    system_prompt: str
    model: str
    context_data: dict[str, Any] | None = None

    llm_response: str | None
    parsed_response: dict[str, Any] | None = None
    operation_type: LLMOperationType
    space_id: UUID | None = None

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    error_message: str | None = None
    duration_ms: int
    created_at: datetime = Field(default_factory=now)
