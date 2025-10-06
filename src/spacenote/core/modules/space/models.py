"""Space models for organizing notes."""

from uuid import UUID

from pydantic import BaseModel, Field

from spacenote.core.db import MongoModel
from spacenote.core.modules.field.models import SpaceField
from spacenote.core.modules.filter.models import Filter


class SpaceTemplates(BaseModel):
    """Templates for customizing space views."""

    note_detail: str | None = Field(None, description="Optional Liquid template for customizing note detail view")
    note_list: str | None = Field(None, description="Optional Liquid template for customizing note list item view")


class Space(MongoModel):
    """Container for notes with custom schemas."""

    slug: str  # URL-friendly unique ID
    title: str
    description: str = ""  # Space description
    members: list[UUID]  # Users with access
    fields: list[SpaceField] = Field(default_factory=list)  # Field definitions (order matters)
    list_fields: list[str] = Field(default_factory=list)  # Default columns in list view
    hidden_create_fields: list[str] = Field(default_factory=list)  # Fields hidden in create form
    comment_editable_fields: list[str] = Field(default_factory=list)  # Fields editable when commenting
    filters: list[Filter] = Field(default_factory=list)  # Saved filter configurations
    templates: SpaceTemplates = SpaceTemplates()  # Templates for customizing views

    def get_field(self, id: str) -> SpaceField | None:
        """Get field definition by id."""
        for field in self.fields:
            if field.id == id:
                return field
        return None

    def get_filter(self, id: str) -> Filter | None:
        """Get filter definition by id."""
        for filter in self.filters:
            if filter.id == id:
                return filter
        return None
