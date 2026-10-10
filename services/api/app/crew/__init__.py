from fastapi import FastAPI

from app.crew import models
from app.crew.models import CrewMember

__all__ = ["CrewMember", "models", "register"]


def register(app: FastAPI) -> None:
    """Includes the crew routers. Called from `create_app`."""
    from app.crew import router

    app.include_router(router.admin)
    app.include_router(router.crew)
