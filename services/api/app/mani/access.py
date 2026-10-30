"""Founder-only access (decision D6). Hiding a menu item is not enough: every Mani route
and stream depends on `require_founder`, which checks the role and the bound login."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.identity.service import User
from app.mani.config import ManiSettings, get_mani_settings
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError

_admin = require_role("admin")


def require_founder(
    user: User = Depends(_admin),
    db: Session = Depends(get_db),
    settings: ManiSettings = Depends(get_mani_settings),
) -> User:
    """The signed-in admin, when their login is the one bound to the Founder."""
    login = db.get(Login, user.id)
    bound = settings.founder_login_id.strip().lower()
    if login is None or not login.active or not bound or login.login_id.strip().lower() != bound:
        raise ApiError("forbidden", "You cannot open this.", 403)
    return user
