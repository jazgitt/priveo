from fastapi import FastAPI

import app.models  # Registers every table, so the links between them resolve.
from app import crew
from app.customers import router as customers
from app.home import router as home
from app.identity import router as identity
from app.platform.errors import install_error_handlers
from app.platform.middleware import RequestIdMiddleware
from app.system import router as system


def create_app() -> FastAPI:
    app = FastAPI(title="Priveo API", version="0.1.0", docs_url=None, redoc_url=None)
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(identity.router)
    app.include_router(identity.admin)
    app.include_router(customers.router)
    app.include_router(home.crew)
    app.include_router(home.admin)
    crew.register(app)
    return app


app = create_app()
