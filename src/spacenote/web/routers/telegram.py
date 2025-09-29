from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from spacenote.core.modules.telegram.models import TelegramEventType, TelegramIntegration, TelegramNotificationConfig
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


class UpdateTelegramIntegrationRequest(BaseModel):
    """Request to update Telegram integration settings.

    All fields are optional to support partial updates - only provide the fields you want to change.
    Fields not included in the request will remain unchanged."""

    bot_token: str | None = Field(
        None, description="New Telegram Bot API token (keep secure!). Optional - only provide to update."
    )
    chat_id: str | None = Field(None, description="New Telegram chat ID. Optional - only provide to update.")
    is_enabled: bool | None = Field(None, description="Enable or disable all notifications. Optional - only provide to update.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "is_enabled": False,
                }
            ]
        }
    }


@router.put(
    "/spaces/{space_slug}/telegram",
    summary="Update Telegram integration",
    description="Update existing Telegram integration settings for a space.",
    operation_id="updateTelegramIntegration",
    responses={
        200: {"description": "Telegram integration updated"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a space member"},
        404: {"model": ErrorResponse, "description": "Space or integration not found"},
    },
)
async def update_telegram_integration(
    app: AppDep, auth_token: AuthTokenDep, space_slug: str, request: UpdateTelegramIntegrationRequest
) -> TelegramIntegration:
    return await app.update_telegram_integration(auth_token, space_slug, request.bot_token, request.chat_id, request.is_enabled)


@router.delete(
    "/spaces/{space_slug}/telegram",
    summary="Delete Telegram integration",
    description="Remove Telegram integration from a space completely.",
    operation_id="deleteTelegramIntegration",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Telegram integration deleted"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a space member"},
        404: {"model": ErrorResponse, "description": "Space or integration not found"},
    },
)
async def delete_telegram_integration(app: AppDep, auth_token: AuthTokenDep, space_slug: str) -> None:
    await app.delete_telegram_integration(auth_token, space_slug)


class UpdateNotificationRequest(BaseModel):
    """Request to update notification configuration."""

    enabled: bool = Field(..., description="Whether this notification type is enabled")
    template: str = Field(..., description="Liquid template for formatting the notification message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "enabled": True,
                    "template": "📝 New note #{{note.number}} in {{space.title}}",
                }
            ]
        }
    }


@router.put(
    "/spaces/{space_slug}/telegram/notifications/{event_type}",
    summary="Update notification configuration",
    description="Update notification settings for a specific event type.",
    operation_id="updateTelegramNotification",
    responses={
        200: {"description": "Notification configuration updated"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a space member"},
        404: {"model": ErrorResponse, "description": "Space or integration not found"},
        400: {"model": ErrorResponse, "description": "Invalid event type"},
    },
)
async def update_telegram_notification(
    app: AppDep,
    auth_token: AuthTokenDep,
    space_slug: str,
    event_type: TelegramEventType,
    request: UpdateNotificationRequest,
) -> TelegramNotificationConfig:
    return await app.update_telegram_notification(auth_token, space_slug, event_type, request.enabled, request.template)


class TestTelegramResponse(BaseModel):
    """Response from testing Telegram integration."""

    success: bool = Field(..., description="Whether the test message was sent successfully")
    error: str | None = Field(None, description="Error details if the test failed")


@router.post(
    "/spaces/{space_slug}/telegram/test",
    summary="Test Telegram integration",
    description="Send a test message to verify Telegram integration is working correctly.",
    operation_id="testTelegramIntegration",
    responses={
        200: {"description": "Test result"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a space member"},
        404: {"model": ErrorResponse, "description": "Space or integration not found"},
    },
)
async def test_telegram_integration(app: AppDep, auth_token: AuthTokenDep, space_slug: str) -> TestTelegramResponse:
    success, error_msg = await app.test_telegram_integration(auth_token, space_slug)
    return TestTelegramResponse(
        success=success,
        error=error_msg,
    )
