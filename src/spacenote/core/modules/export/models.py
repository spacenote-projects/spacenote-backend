"""Export/import models for space data portability."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from spacenote.core.modules.field.models import SpaceField
from spacenote.core.modules.filter.models import Filter
from spacenote.core.modules.space.models import SpaceTemplates


class ExportSpace(BaseModel):
    """Space representation for export without system-specific IDs."""

    # Force unified schema for both input/output in OpenAPI to avoid ExportSpace-Input/Output duplication
    model_config = ConfigDict(json_schema_mode_override="validation")

    slug: str
    title: str
    description: str
    members: list[str] = Field(..., description="Member usernames (not UUIDs)")
    fields: list[SpaceField]
    list_fields: list[str]
    hidden_create_fields: list[str]
    filters: list[Filter]
    templates: SpaceTemplates


class ExportData(BaseModel):
    """Complete export package with metadata."""

    # Force unified schema for both input/output in OpenAPI to avoid ExportData-Input/Output duplication
    model_config = ConfigDict(json_schema_mode_override="validation")

    space: ExportSpace
    exported_at: datetime
    spacenote_version: str
