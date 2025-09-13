from spacenote.web.routers.auth import router as auth_router
from spacenote.web.routers.comments import router as comments_router
from spacenote.web.routers.notes import router as notes_router
from spacenote.web.routers.profile import router as profile_router
from spacenote.web.routers.spaces import router as spaces_router
from spacenote.web.routers.users import router as users_router

__all__ = ["auth_router", "comments_router", "notes_router", "profile_router", "spaces_router", "users_router"]
