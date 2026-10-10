"""Visits and jobs for the crew app. `register(app)` adds the routes."""
from fastapi import FastAPI


def register(api: FastAPI) -> None:
    import app.visits.models  # noqa: F401  (registers the tables)
    from app.visits.router import router

    api.include_router(router)
