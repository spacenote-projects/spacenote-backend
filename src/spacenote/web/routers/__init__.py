from spacenote.web.routers.attachments import router as attachments_router
from spacenote.web.routers.auth import router as auth_router
from spacenote.web.routers.comments import router as comments_router
from spacenote.web.routers.export import router as export_router
from spacenote.web.routers.fields import router as fields_router
from spacenote.web.routers.filters import router as filters_router
from spacenote.web.routers.llm import router as llm_router
from spacenote.web.routers.metadata import router as metadata_router
from spacenote.web.routers.notes import router as notes_router
from spacenote.web.routers.profile import router as profile_router
from spacenote.web.routers.spaces import router as spaces_router
from spacenote.web.routers.telegram import router as telegram_router
from spacenote.web.routers.users import router as users_router

__all__ = [
    "attachments_router",
    "auth_router",
    "comments_router",
    "export_router",
    "fields_router",
    "filters_router",
    "llm_router",
    "metadata_router",
    "notes_router",
    "profile_router",
    "spaces_router",
    "telegram_router",
    "users_router",
]
