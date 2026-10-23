"""Admin-controlled feature flags (ADM-FLAG). The admin portal switches a
feature on or off; the apps read the flags on sign-in and on a hard refresh,
never on a timer. Call `register(app)` from `create_app`. Endpoints guard a
switched-off feature with `require_feature(key)`."""
from fastapi import FastAPI

from app.features import models  # noqa: F401  (registers the table)


def register(app: FastAPI) -> None:
    from app.features import router

    app.include_router(router.admin)
    app.include_router(router.customer)
    app.include_router(router.crew)
