from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from spacenote.core.modules.note.models import Note
from spacenote.core.pagination import PaginationResult
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router: APIRouter = APIRouter(tags=["notes"])


class CreateNoteRequest(BaseModel):
    """Request to create a new note."""

    raw_fields: dict[str, str] = Field(
        ...,
        description="Field values as raw strings (will be parsed according to field types)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "raw_fields": {
                        "title": "Complete API documentation",
                        "description": "Add comprehensive OpenAPI documentation",
                        "status": "in_progress",
                        "priority": "high",
                    }
                }
            ]
        }
    }


class UpdateNoteFieldsRequest(BaseModel):
    """Request to update note fields (partial update)."""

    raw_fields: dict[str, str] = Field(
        ...,
        description="Field values to update as raw strings. Only provided fields will be updated (partial update).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "raw_fields": {
                        "title": "Updated title",
                        "status": "completed",
                    }
                }
            ]
        }
    }


@router.get(
    "/spaces/{space_slug}/notes",
    summary="List space notes",
    description="Get paginated notes in a space. Only space members can view notes.",
    operation_id="listNotes",
    responses={
        200: {"description": "Paginated list of notes"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def list_notes(
    space_slug: str,
    app: AppDep,
    auth_token: AuthTokenDep,
    limit: Annotated[int, Query(ge=1, description="Maximum items to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> PaginationResult[Note]:
    return await app.get_notes_by_space(auth_token, space_slug, limit, offset)


@router.get(
    "/spaces/{space_slug}/notes/{number}",
    summary="Get note by number",
    description="Get a specific note by its number within a space. Only space members can view notes.",
    operation_id="getNote",
    responses={
        200: {"description": "Note details"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def get_note_by_number(space_slug: str, number: int, app: AppDep, auth_token: AuthTokenDep) -> Note:
    return await app.get_note_by_number(auth_token, space_slug, number)


@router.post(
    "/spaces/{space_slug}/notes",
    summary="Create new note",
    description="Create a new note in a space with the provided field values. Only space members can create notes.",
    operation_id="createNote",
    status_code=201,
    responses={
        201: {"description": "Note created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid field data or validation failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def create_note(space_slug: str, request: CreateNoteRequest, app: AppDep, auth_token: AuthTokenDep) -> Note:
    return await app.create_note(auth_token, space_slug, request.raw_fields)


@router.patch(
    "/spaces/{space_slug}/notes/{number}",
    summary="Update note fields",
    description=(
        "Partially update fields of an existing note. Only the fields provided will be updated, "
        "all other fields remain unchanged. Only space members can update notes."
    ),
    operation_id="updateNoteFields",
    responses={
        200: {"description": "Note updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid field data or validation failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def update_note_fields(
    space_slug: str, number: int, request: UpdateNoteFieldsRequest, app: AppDep, auth_token: AuthTokenDep
) -> Note:
    return await app.update_note_fields(auth_token, space_slug, number, request.raw_fields)
