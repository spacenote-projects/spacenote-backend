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
        description=(
            "Field values as raw strings (will be parsed according to field types).\n\n"
            "**Datetime fields** accept these formats (all in UTC timezone):\n"
            "- `2025-10-20T10:31` (ISO without seconds)\n"
            "- `2025-10-20T10:31:00` (ISO with seconds)\n"
            "- `2025-10-20T10:31:00.123456` (ISO with microseconds)\n"
            "- `2025-10-20T10:31:00Z` (ISO with Z suffix)\n"
            "- `2025-10-20 10:31:00` (space-separated)\n"
            "- `2025-10-20` (date only, time defaults to 00:00:00)\n"
            "- `$now` (special value for current UTC time)\n\n"
            "⚠️ **Important**: All datetime values must be in UTC timezone. "
            "Timezone offsets (e.g., `+03:00`, `-05:00`) are not supported. "
            "All datetime values in responses are returned with `+00:00` suffix to indicate UTC "
            "(e.g., `2025-10-20T10:31:00+00:00`).\n\n"
            "**Other field types**:\n"
            "- String/Markdown: Any text value\n"
            "- Boolean: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`\n"
            "- Int/Float: Numeric values as strings (e.g., `42`, `3.14`)\n"
            "- Select: Must match one of the allowed values\n"
            "- Tags: Comma-separated values (e.g., `tag1,tag2,tag3`)\n"
            "- User: Username, user ID (UUID), or `$me` for current user\n"
            "- Image: Attachment UUID"
        ),
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
        description=(
            "Field values to update as raw strings. Only provided fields will be updated (partial update).\n\n"
            "See the `createNote` operation for detailed format examples and requirements for each field type."
        ),
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
    description="""Get paginated notes in a space with optional filtering.

**Filtering options:**
- Use `filter` parameter to apply a saved filter by ID
- Use `q` parameter for ad-hoc filtering with syntax: `field:operator:value,field:operator:value`

When both are provided, conditions are combined with AND logic.

**URL Encoding:**
⚠️ Values containing special characters MUST be URL-encoded:
- Spaces and symbols: `title:contains:hello%20world`
- **JSON arrays (for `in`, `nin`, `all` operators) MUST be URL-encoded:**
  - Raw: `["tag1","tag2"]`
  - Encoded: `%5B%22tag1%22%2C%22tag2%22%5D`
  - Full example: `?q=tags:in:%5B%22shopping%22%2C%22groceries%22%5D`

**System fields:**
Available for filtering without prefix:
- `number` - Note number
- `user_id` - Author ID (use with `$me` for current user)
- `created_at` - Creation timestamp
- `edited_at` - Last edit timestamp
- `commented_at` - Last comment timestamp
- `activity_at` - Last activity timestamp

Custom fields are used directly by their field ID.

**Value types:**
- Null: `field:eq:null`
- Boolean: `field:eq:true` or `field:eq:false`
- Numbers: Parsed automatically (`priority:gte:5`)
- Strings: Use as-is (`status:eq:active`)
- Special: `$me` resolves to current user ID

**Examples:**
- Single condition: `?q=status:eq:active`
- Multiple conditions: `?q=status:eq:active,priority:gte:5`
- With URL encoding: `?q=title:contains:hello%20world`
- Array values (URL-encoded): `?q=tags:in:%5B%22shopping%22%2C%22groceries%22%5D`
- Special value: `?q=user_id:eq:$me`
- System fields: `?q=number:gt:100,created_at:gte:2024-01-01`
- Combined with saved filter: `?filter=my-tasks&q=tags:in:%5B%22urgent%22%5D`

Only space members can view notes.""",
    operation_id="listNotes",
    responses={
        200: {"description": "Paginated list of notes"},
        400: {"model": ErrorResponse, "description": "Invalid query syntax or validation error"},
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
    filter: Annotated[str | None, Query(description="Optional filter id to apply")] = None,
    q: Annotated[str | None, Query(description="Ad-hoc query conditions (field:operator:value,...)")] = None,
) -> PaginationResult[Note]:
    return await app.get_notes_by_space(auth_token, space_slug, limit, offset, filter, q)


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
