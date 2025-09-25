"""Shared pytest fixtures."""

from uuid import UUID

import pytest

from spacenote.core.modules.space.models import Space
from spacenote.core.modules.user.models import User


@pytest.fixture
def mock_space():
    """Create a mock space for testing."""
    return Space(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        slug="test-space",
        title="Test Space",
        description="Test space for unit tests",
        created_at=None,  # Will be set by the model
        updated_at=None,  # Will be set by the model
        members=[UUID("87654321-4321-8765-4321-876543218765")],
        fields=[],
    )


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        id=UUID("87654321-4321-8765-4321-876543218765"),
        username="testuser",
        password_hash="$2b$12$hashed_password_here",
    )


@pytest.fixture
def mock_members(mock_user):
    """Create a list of mock members."""
    return [mock_user]
