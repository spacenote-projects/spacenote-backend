from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel
from spacenote.utils import now


class LLMOperationType(str, Enum):
    """LLM operation types."""

    CREATE_NOTE = "create_note"
    UPDATE_NOTE = "update_note"
    CREATE_COMMENT = "create_comment"


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


class LLMLog(MongoModel):
    """Log of LLM API interaction."""

    user_id: UUID
    user_input: str
    system_prompt: str
    model: str
    context_data: dict[str, Any] | None = None

    llm_response: str | None
    parsed_response: dict[str, Any] | None = None
    operation_type: LLMOperationType | None = None
    space_id: UUID | None = None

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    error_message: str | None = None
    duration_ms: int
    created_at: datetime = Field(default_factory=now)
