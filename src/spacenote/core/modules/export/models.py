"""Export/import models for space data portability."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from spacenote.core.modules.field.models import FieldValueType, SpaceField
from spacenote.core.modules.filter.models import Filter
from spacenote.core.modules.space.models import SpaceTemplates
from spacenote.core.modules.telegram.models import TelegramEventType, TelegramNotificationConfig


class ExportTelegramConfig(BaseModel):
    """Telegram integration configuration for export (excludes sensitive credentials)."""

    is_enabled: bool = Field(..., description="Whether telegram integration is enabled")
    notifications: dict[TelegramEventType, TelegramNotificationConfig] = Field(
        ..., description="Notification configuration for each event type"
    )


class ExportNote(BaseModel):
    """Note representation for export without system-specific IDs."""

    number: int = Field(..., description="Note number within the space")
    username: str = Field(..., description="Username of note creator (not UUID)")
    created_at: datetime
    edited_at: datetime | None = None
    commented_at: datetime | None = None
    activity_at: datetime
    fields: dict[str, FieldValueType] = Field(..., description="Field values")


class ExportComment(BaseModel):
    """Comment representation for export without system-specific IDs."""

    note_number: int = Field(..., description="Number of the note this comment belongs to")
    number: int = Field(..., description="Comment number within the note")
    username: str = Field(..., description="Username of comment author (not UUID)")
    content: str
    created_at: datetime
    edited_at: datetime | None = None


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
    telegram: ExportTelegramConfig | None = Field(None, description="Telegram integration configuration (excludes credentials)")


class ExportData(BaseModel):
    """Complete export package with metadata."""

    # Force unified schema for both input/output in OpenAPI to avoid ExportData-Input/Output duplication
    model_config = ConfigDict(json_schema_mode_override="validation")

    space: ExportSpace
    notes: list[ExportNote] | None = Field(None, description="Notes data (when include_data=true)")
    comments: list[ExportComment] | None = Field(None, description="Comments data (when include_data=true)")
    exported_at: datetime
    spacenote_version: str
