"""Deep Spa requests (ADD-, ADM-ADD-)."""
from fastapi import FastAPI


def register(app: FastAPI) -> None:
    from app.addons import models  # noqa: F401  (registers the tables)
    from app.addons.router import admin, customer

    app.include_router(customer)
    app.include_router(admin)
