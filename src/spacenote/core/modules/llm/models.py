from typing import Any, Literal

from pydantic import BaseModel, Field


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


class IntentClassification(BaseModel):
    """Classification of user intent from natural language."""

    space_slug: str = Field(..., description="Slug of the space to operate on")
    operation_type: Literal["create_note", "update_note", "create_comment"] = Field(
        ..., description="Type of operation to perform"
    )
