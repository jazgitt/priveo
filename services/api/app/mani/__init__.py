"""Mani Bond, the Founder's Chief of Staff (docs/agent/). Founder-only. Call
`register(app)` from `create_app`. Phase 1 is text only: answer, cite, remember and draft
proposals; no tool changes a business record."""
from fastapi import FastAPI

from app.mani import models  # noqa: F401  (registers the tables)


def register(app: FastAPI) -> None:
    from app.mani import cron, router

    app.include_router(router.admin)
    cron.register(app)
