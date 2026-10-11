"""Reference data: societies, plans, vehicle catalogue, services, working
slots, checklists, could-not-complete reasons, settings and the add-on
catalogue (ADM-REF, ADM-SET, ADM-SVS, ADM-CHK, ADM-CNC, ADM-ADD).

Call `register(app)` from `create_app`. Other modules read the data through
`app.directory.lookup`. `app.directory.seed.seed_defaults(db)` inserts the
starting data and is safe to run again.
"""
from fastapi import FastAPI

from app.directory import models  # noqa: F401  (registers the tables)


def register(app: FastAPI) -> None:
    from app.directory import router

    app.include_router(router.admin)
    app.include_router(router.customer)
