from typing import Any
from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from spacenote.core.core import Service
from spacenote.core.modules.filter.models import Filter


class FilterService(Service):
    """Service for filter validation and management."""

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        super().__init__(database)

    def validate_filter_definition(self, space_id: UUID, filter: Filter) -> Filter:
        """Validate filter definition.

        Args:
            space_id: The space ID for this validation
            filter: The filter definition to validate

        Returns:
            A validated Filter.

        Raises:
            ValidationError: If filter is invalid
            NotFoundError: If space not found
        """
        raise NotImplementedError

    async def add_filter_to_space(self, space_id: UUID, filter: Filter) -> None:
        """Add a filter to a space with validation.

        Args:
            space_id: The space to add the filter to
            filter: The filter definition to add

        Raises:
            ValidationError: If filter already exists or is invalid
            NotFoundError: If space not found
        """
        raise NotImplementedError

    async def remove_filter_from_space(self, space_id: UUID, filter_name: str) -> None:
        """Remove a filter from a space.

        Args:
            space_id: The space to remove the filter from
            filter_name: The name of the filter to remove

        Raises:
            NotFoundError: If space or filter not found
        """
        raise NotImplementedError
