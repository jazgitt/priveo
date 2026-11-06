"""Route modules dropped into this folder are included by `scheduling.register`
(see app.scheduling.hooks). A module defines `router` or `routers`, and may set
`ORDER`."""
from types import ModuleType

from fastapi import APIRouter

from app.scheduling import hooks


def discover() -> list[ModuleType]:
    return hooks.discover_in(__name__, __path__)


def routers() -> list[APIRouter]:
    found: list[APIRouter] = []
    for module in discover():
        found.extend(getattr(module, "routers", None) or [])
        if getattr(module, "router", None) is not None:
            found.append(module.router)
    return found
