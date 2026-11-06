"""Modules dropped into this folder are found automatically (see
app.scheduling.hooks). A module may define `provide` and `ORDER`."""
from types import ModuleType

from app.scheduling import hooks


def discover() -> list[ModuleType]:
    return hooks.discover_in(__name__, __path__)
