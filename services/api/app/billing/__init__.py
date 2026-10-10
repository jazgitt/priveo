"""Payments by UPI, billing cycles, invoices and the overdue job (PAY-, SUB-, ADM-PAY-)."""
from fastapi import FastAPI


def register(app: FastAPI) -> None:
    from app.billing import models  # noqa: F401  (registers the tables)
    from app.billing.router import admin, customer

    app.include_router(customer)
    app.include_router(admin)
