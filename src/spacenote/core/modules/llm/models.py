from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal
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
    """Intent to create a new note in a space."""

    operation_type: Literal["create_note"] = "create_note"
    space_slug: str = Field(..., description="Slug of the space to create note in")
    fields: dict[str, str] = Field(..., description="Field values for the new note as strings")


class UpdateNoteIntent(BaseModel):
    """Intent to update an existing note."""

    operation_type: Literal["update_note"] = "update_note"
    space_slug: str = Field(..., description="Slug of the space containing the note")
    note_number: int = Field(..., description="Note number to update")
    fields: dict[str, str] = Field(..., description="Field values to update as strings")


class CreateCommentIntent(BaseModel):
    """Intent to create a comment on a note."""

    operation_type: Literal["create_comment"] = "create_comment"
    space_slug: str = Field(..., description="Slug of the space containing the note")
    note_number: int = Field(..., description="Note number to comment on")
    content: str = Field(..., description="Comment text content")


Intent = Annotated[
    CreateNoteIntent | UpdateNoteIntent | CreateCommentIntent,
    Field(discriminator="operation_type"),
]


class IntentClassification(BaseModel):
    """Wrapper model for LLM response containing classified intent."""

    intent: Intent


class LLMLog(MongoModel):
    """Log of LLM API interaction."""

    user_input: str
    llm_response: str | None
    parsed_response: dict[str, Any] | None = None

    user_id: UUID
    created_at: datetime = Field(default_factory=now)

    operation_type: LLMOperationType
    space_id: UUID | None = None
    system_prompt: str
    context_data: dict[str, Any] | None = None

    model: str

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    error_message: str | None = None
    duration_ms: int
