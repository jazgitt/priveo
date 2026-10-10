"""Photo and video uploads through signed URLs. `register(app)` adds the routes."""
from fastapi import FastAPI


def register(api: FastAPI) -> None:
    import app.media.models  # noqa: F401  (registers the tables)
    from app.media.router import router

    api.include_router(router)
