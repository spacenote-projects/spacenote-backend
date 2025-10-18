from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse

from spacenote.core.modules.attachment.models import Attachment
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["attachments"])


@router.post(
    "/spaces/{space_slug}/attachments",
    summary="Upload attachment",
    description=(
        "Upload a file attachment to a space. Optionally attach directly to a note. "
        "Returns attachment metadata with ID that can be used in IMAGE fields."
    ),
    operation_id="uploadAttachment",
    status_code=201,
    responses={
        201: {"description": "Attachment uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or validation failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def upload_attachment(
    space_slug: str, file: UploadFile, app: AppDep, auth_token: AuthTokenDep, note_number: int | None = None
) -> Attachment:
    content = await file.read()
    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"
    return await app.upload_attachment(auth_token, space_slug, filename, content, mime_type, note_number)


@router.get(
    "/spaces/{space_slug}/notes/{note_number}/attachments",
    summary="List note attachments",
    description="Get all attachments for a specific note.",
    operation_id="listNoteAttachments",
    responses={
        200: {"description": "List of attachments"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or note not found"},
    },
)
async def list_note_attachments(space_slug: str, note_number: int, app: AppDep, auth_token: AuthTokenDep) -> list[Attachment]:
    return await app.get_note_attachments(auth_token, space_slug, note_number)


@router.get(
    "/spaces/{space_slug}/attachments/{attachment_number}",
    summary="Download attachment",
    description="Download the original attachment file by number.",
    operation_id="downloadAttachment",
    responses={
        200: {"description": "Attachment file"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or attachment not found"},
    },
)
async def download_attachment(space_slug: str, attachment_number: int, app: AppDep, auth_token: AuthTokenDep) -> FileResponse:
    file_info = await app.get_attachment_file_info(auth_token, space_slug, attachment_number)
    return FileResponse(path=file_info.file_path, media_type=file_info.mime_type, filename=file_info.filename)
