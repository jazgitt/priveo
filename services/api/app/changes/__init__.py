"""Skip, un-skip, pause and cutoff-time changes (SKIP-, PAUSE-, SCHED-01)."""
from fastapi import FastAPI


def register(app: FastAPI) -> None:
    from app.changes import models  # noqa: F401  (registers the tables)
    from app.changes.router import admin, customer

    app.include_router(customer)
    app.include_router(admin)
