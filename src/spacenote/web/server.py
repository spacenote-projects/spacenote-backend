from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from spacenote.app import App
from spacenote.config import Config
from spacenote.errors import UserError
from spacenote.web.error_handlers import general_exception_handler, user_error_handler
from spacenote.web.openapi import set_custom_openapi
from spacenote.web.routers import (
    attachments_router,
    auth_router,
    comments_router,
    export_router,
    fields_router,
    filters_router,
    images_router,
    llm_router,
    metadata_router,
    notes_router,
    profile_router,
    spaces_router,
    telegram_router,
    users_router,
)


def create_fastapi_app(app_instance: App, config: Config) -> FastAPI:
    """Create and configure FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """FastAPI application lifespan management."""
        # Store app instance and config in app state
        app.state.app = app_instance
        app.state.config = config
        async with app_instance.lifespan():
            yield

    app = FastAPI(
        title="SpaceNote API",
        lifespan=lifespan,
        openapi_tags=[],  # Tags will be added by custom OpenAPI function
    )

    app.add_middleware(SessionMiddleware, secret_key=config.session_secret_key)

    # Add CORS middleware for frontend development
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Health check endpoint (at root level, not versioned)
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    # API v1 routes
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(profile_router, prefix="/api/v1")
    app.include_router(spaces_router, prefix="/api/v1")
    app.include_router(fields_router, prefix="/api/v1")
    app.include_router(filters_router, prefix="/api/v1")
    app.include_router(notes_router, prefix="/api/v1")
    app.include_router(comments_router, prefix="/api/v1")
    app.include_router(attachments_router, prefix="/api/v1")
    app.include_router(images_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")
    app.include_router(telegram_router, prefix="/api/v1")
    app.include_router(llm_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(metadata_router)

    # Register error handlers
    app.add_exception_handler(UserError, user_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    set_custom_openapi(app)

    return app
