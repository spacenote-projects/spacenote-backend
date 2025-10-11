from typing import Annotated, Any, Literal

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
