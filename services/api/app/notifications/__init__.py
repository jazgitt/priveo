from fastapi import FastAPI


def register(app: FastAPI) -> None:
    # Importing the models registers the tables with the database metadata.
    from app.notifications import models  # noqa: F401
    from app.notifications.router import router

    app.include_router(router)
