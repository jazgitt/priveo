from fastapi import FastAPI

from app.webauth.router import WebAuthLoginRequest, WebAuthProfile

__all__ = ["WebAuthLoginRequest", "WebAuthProfile", "register"]


def register(app: FastAPI) -> None:
    """Includes the browser sign-in routes and the portal's static files.
    Called from `create_app`."""
    from app.webauth import portal, router

    app.include_router(router.router)
    app.include_router(portal.router)
