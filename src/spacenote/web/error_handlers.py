import logging

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from spacenote.errors import AccessDeniedError, AuthenticationError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


def create_json_error_response(status_code: int, message: str, error_type: str | None = None) -> JSONResponse:
    """Create JSON error response with optional type for machine parsing."""
    content = {"message": message}
    if error_type:
        content["type"] = error_type
    return JSONResponse(status_code=status_code, content=content)


async def user_error_handler(_: Request, exc: Exception) -> Response:
    """Handle all UserError subclasses with appropriate status codes."""
    # Determine the appropriate status code and type based on error
    if isinstance(exc, AuthenticationError):
        status_code = 401
        error_type = "authentication_error"
    elif isinstance(exc, AccessDeniedError):
        status_code = 403
        error_type = "access_denied"
    elif isinstance(exc, NotFoundError):
        status_code = 404
        error_type = "not_found"
    elif isinstance(exc, ValidationError):
        status_code = 400
        error_type = "validation_error"
    else:
        # Default for any other UserError subclass
        status_code = 400
        error_type = "bad_request"

    return create_json_error_response(status_code=status_code, message=str(exc), error_type=error_type)


async def general_exception_handler(_: Request, exc: Exception) -> Response:
    """Handle unexpected errors (500)."""
    logger.exception("Unexpected error: %s", exc)
    return create_json_error_response(
        status_code=500, message="An unexpected error occurred.", error_type="internal_server_error"
    )
