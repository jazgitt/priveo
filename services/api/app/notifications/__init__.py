from fastapi import FastAPI


def register(app: FastAPI) -> None:
    # Importing the models registers the tables with the database metadata.
    from app.notifications import models  # noqa: F401
    from app.notifications.cron import router as cron
    from app.notifications.router import admin_router, crew_router, router

    app.include_router(router)
    app.include_router(crew_router)
    app.include_router(admin_router)
    app.include_router(cron)
