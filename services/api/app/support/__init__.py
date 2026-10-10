"""Support and feedback: complaints, feedback, visit ratings, monthly check-ins
and admin alerts (ISS-, CMP-, FDBK-, CHK-, ADM-CMP, ADM-FDB).

Call `register(app)` from `create_app`. Importing this package also registers
its tables with the database metadata.
"""
from fastapi import FastAPI

from app.support import models  # noqa: F401  (registers the tables)


def register(app: FastAPI) -> None:
    from app.support import router

    app.include_router(router.customer)
    app.include_router(router.crew)
    app.include_router(router.admin)
