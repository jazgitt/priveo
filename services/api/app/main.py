from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # Registers every table, so the links between them resolve.
from app import (
    addons,
    billing,
    changes,
    crew,
    customer_reads,
    directory,
    features,
    mani,
    media,
    notifications,
    scheduling,
    support,
    visits,
    webauth,
)
from app.customers import administration, plan_changes, schedule_pattern, service_history
from app.customers import parking as vehicle_parking
from app.customers import router as customers
from app.home import router as home
from app.identity import router as identity
from app.notifications.cron import get_cron_settings
from app.platform.config import check_startup, get_settings
from app.platform.errors import install_error_handlers
from app.platform.middleware import RequestIdMiddleware
from app.scheduling import administration as scheduling_admin
from app.system import router as system
from app.visits import operations


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    check_startup(get_settings(), cron_secret=get_cron_settings().cron_secret)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Priveo API", version="0.1.0", docs_url=None, redoc_url=None,
                  lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(identity.router)
    app.include_router(identity.admin)
    app.include_router(customers.router)
    app.include_router(administration.admin)
    app.include_router(vehicle_parking.admin)
    app.include_router(plan_changes.admin)
    app.include_router(schedule_pattern.admin)
    app.include_router(service_history.admin)
    app.include_router(administration.customer)
    app.include_router(scheduling_admin.router)
    app.include_router(operations.router)
    app.include_router(home.crew)
    app.include_router(home.admin)
    crew.register(app)
    scheduling.register(app)
    customer_reads.register(app)
    notifications.register(app)
    support.register(app)
    visits.register(app)
    media.register(app)
    changes.register(app)
    billing.register(app)
    addons.register(app)
    webauth.register(app)
    directory.register(app)
    features.register(app)
    mani.register(app)
    return app


app = create_app()
