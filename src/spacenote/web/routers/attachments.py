from fastapi import APIRouter, UploadFile

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
