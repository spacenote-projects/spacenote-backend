from typing import Any

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
