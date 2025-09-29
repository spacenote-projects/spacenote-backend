from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from spacenote.core.modules.telegram.models import TelegramIntegration
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(tags=["telegram"])


class CreateTelegramIntegrationRequest(BaseModel):
    """Request to create a new Telegram integration."""

    bot_token: str = Field(..., description="Telegram Bot API token (keep secure!)")
    chat_id: str = Field(..., description="Telegram chat ID (can be numeric ID or @username for public channels)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
                    "chat_id": "-1001234567890",
                }
            ]
        }
    }


@router.get(
    "/spaces/{space_slug}/telegram",
    summary="Get Telegram integration",
    description="Get the Telegram integration configuration for a space.",
    operation_id="getTelegramIntegration",
    responses={
        200: {"description": "Telegram integration configuration or null if not configured"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a space member"},
        404: {"model": ErrorResponse, "description": "Space not found"},
    },
)
async def get_telegram_integration(app: AppDep, auth_token: AuthTokenDep, space_slug: str) -> TelegramIntegration | None:
    return await app.get_telegram_integration(auth_token, space_slug)


@router.post(
    "/spaces/{space_slug}/telegram",
    summary="Create Telegram integration",
    description="Create a new Telegram integration for the space with default notification templates.",
    operation_id="createTelegramIntegration",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Telegram integration created"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a space member"},
        404: {"model": ErrorResponse, "description": "Space not found"},
        400: {"model": ErrorResponse, "description": "Invalid request data or integration already exists"},
    },
)
async def create_telegram_integration(
    app: AppDep, auth_token: AuthTokenDep, space_slug: str, request: CreateTelegramIntegrationRequest
) -> TelegramIntegration:
    return await app.create_telegram_integration(auth_token, space_slug, request.bot_token, request.chat_id)
