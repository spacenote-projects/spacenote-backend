from uuid import UUID

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse

from spacenote.core.modules.attachment.models import Attachment
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["attachments"])


@router.post(
    "/spaces/{space_slug}/attachments",
    summary="Upload attachment",
    description="Upload a file attachment to a space. Returns attachment metadata with ID that can be used in IMAGE fields.",
    operation_id="uploadAttachment",
    status_code=201,
    responses={
        201: {"description": "Attachment uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or validation failed"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def upload_attachment(space_slug: str, file: UploadFile, app: AppDep, auth_token: AuthTokenDep) -> Attachment:
    content = await file.read()
    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"
    return await app.upload_attachment(auth_token, space_slug, filename, content, mime_type)


@router.get(
    "/spaces/{space_slug}/attachments/{attachment_id}",
    summary="Download attachment",
    description="Download the original attachment file.",
    operation_id="downloadAttachment",
    responses={
        200: {"description": "Attachment file"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space or attachment not found"},
    },
)
async def download_attachment(space_slug: str, attachment_id: UUID, app: AppDep, auth_token: AuthTokenDep) -> FileResponse:
    file_info = await app.get_attachment_path(auth_token, space_slug, attachment_id)
    return FileResponse(
        path=file_info.file_path,
        media_type=file_info.mime_type,
        filename=file_info.filename,
    )


@router.get(
    "/spaces/{space_slug}/notes/{note_number}/fields/{field_id}/previews/{preview_key}",
    summary="Download image preview",
    description="Download a preview image for an IMAGE field. Preview is generated based on field's preview configuration.",
    operation_id="downloadPreview",
    responses={
        200: {"description": "Preview image (WebP format)"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space, note, field, or preview not found"},
    },
)
async def download_preview(
    space_slug: str, note_number: int, field_id: str, preview_key: str, app: AppDep, auth_token: AuthTokenDep
) -> FileResponse:
    file_path = await app.get_image_preview_path(auth_token, space_slug, note_number, field_id, preview_key)
    return FileResponse(
        path=file_path,
        media_type="image/webp",
    )
