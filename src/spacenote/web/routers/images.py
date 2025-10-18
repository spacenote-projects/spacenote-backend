from fastapi import APIRouter
from fastapi.responses import FileResponse

from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["images"])


@router.get(
    "/spaces/{space_slug}/notes/{note_number}/images/{field_id}",
    summary="Download image",
    description="Download the image for an IMAGE field. Image is generated based on field's max_width configuration.",
    operation_id="downloadImage",
    responses={
        200: {"description": "Image (WebP format)"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a member of this space"},
        404: {"model": ErrorResponse, "description": "Space, note, field, or image not found"},
    },
)
async def download_image(space_slug: str, note_number: int, field_id: str, app: AppDep, auth_token: AuthTokenDep) -> FileResponse:
    file_path = await app.get_image_path(auth_token, space_slug, note_number, field_id)
    return FileResponse(path=file_path, media_type="image/webp")
