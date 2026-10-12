"""Scheduling (Phase 3): capacity, the OR-Tools scheduler, Draft and Frozen
schedules, and the read models other modules use for the next service and the
crew's day. Wire it in with `register(app)`."""

from fastapi import FastAPI

from app.scheduling.models import (  # noqa: F401
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    SchedulingEvent,
    Visit,
)


def register(app: FastAPI) -> None:
    from app.scheduling import router

    app.include_router(router.customer)
    app.include_router(router.crew)
    app.include_router(router.admin)
