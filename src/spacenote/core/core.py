from __future__ import annotations

import importlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast
from urllib.parse import urlparse

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from spacenote.config import Config


class Service:
    """Base class for services with direct database access."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        self.database = database
        self._core: Core | None = None

    async def on_start(self) -> None:
        """Initialize service on application startup."""

    async def on_stop(self) -> None:
        """Cleanup service on application shutdown."""

    @property
    def core(self) -> Core:
        """Get the core application context."""
        if self._core is None:
            raise RuntimeError("Core not set for service")
        return self._core

    def set_core(self, core: Core) -> None:
        """Set the core application context."""
        self._core = core


class Services:
    """Service registry that automatically discovers and initializes services."""

    from spacenote.core.modules.access.service import AccessService  # noqa: PLC0415
    from spacenote.core.modules.comment.service import CommentService  # noqa: PLC0415
    from spacenote.core.modules.counter.service import CounterService  # noqa: PLC0415
    from spacenote.core.modules.note.service import NoteService  # noqa: PLC0415
    from spacenote.core.modules.session.service import SessionService  # noqa: PLC0415
    from spacenote.core.modules.space.service import SpaceService  # noqa: PLC0415
    from spacenote.core.modules.user.service import UserService  # noqa: PLC0415

    user: UserService
    space: SpaceService
    session: SessionService
    access: AccessService
    counter: CounterService
    note: NoteService
    comment: CommentService

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        """Initialize all services automatically using service configuration."""
        self._services: list[Service] = []
        self._database = database

        # Service configuration: (attribute_name, module_path, class_name)
        # Order matters for initialization - user and space must be first
        service_configs = [
            ("user", "spacenote.core.modules.user.service", "UserService"),
            ("space", "spacenote.core.modules.space.service", "SpaceService"),
            ("session", "spacenote.core.modules.session.service", "SessionService"),
            ("access", "spacenote.core.modules.access.service", "AccessService"),
            ("counter", "spacenote.core.modules.counter.service", "CounterService"),
            ("note", "spacenote.core.modules.note.service", "NoteService"),
            ("comment", "spacenote.core.modules.comment.service", "CommentService"),
        ]

        # Dynamically import and instantiate services
        for attr_name, module_path, class_name in service_configs:
            module = importlib.import_module(module_path)
            service_class = cast(type[Service], getattr(module, class_name))
            service_instance = service_class(database)
            setattr(self, attr_name, service_instance)
            self._services.append(service_instance)

    def set_core(self, core: Core) -> None:
        """Set core reference for all services."""
        for service in self._services:
            service.set_core(core)

    async def start_all(self) -> None:
        """Start all services that have startup logic."""
        for service in self._services:
            if hasattr(service, "on_start"):
                await service.on_start()

    async def stop_all(self) -> None:
        """Stop all services that have cleanup logic."""
        for service in self._services:
            if hasattr(service, "on_stop"):
                await service.on_stop()


class Core:
    """Container providing config, database, and all service instances."""

    config: Config
    mongo_client: AsyncMongoClient[dict[str, Any]]
    database: AsyncDatabase[dict[str, Any]]
    services: Services

    def __init__(self, config: Config) -> None:
        """Initialize core with config, MongoDB, and auto-register services."""
        self.config = config
        self.mongo_client = AsyncMongoClient(config.database_url, uuidRepresentation="standard")
        self.database = self.mongo_client.get_database(urlparse(config.database_url).path[1:])
        self.services = Services(self.database)
        self.services.set_core(self)

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None]:
        """Manage application lifecycle - startup and shutdown."""
        await self.on_start()
        try:
            yield
        finally:
            await self.on_stop()

    async def on_start(self) -> None:
        """Start all services on application startup."""
        await self.services.start_all()

    async def on_stop(self) -> None:
        """Stop services and close MongoDB connection on shutdown."""
        await self.services.stop_all()
        await self.mongo_client.aclose()
