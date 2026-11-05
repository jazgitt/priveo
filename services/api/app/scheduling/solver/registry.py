"""Finds the solver rule modules in `solver/rules/`, in a fixed order."""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from types import ModuleType

from app.scheduling.solver import rules as rules_package

DEFAULT_PRIORITY = 100


@dataclass(frozen=True)
class Rule:
    name: str
    priority: int
    module: ModuleType

    def add_job_terms(self, ctx, job) -> None:
        hook = getattr(self.module, "add_job_terms", None)
        if hook is not None:
            hook(ctx, job)

    def add_day_terms(self, ctx) -> None:
        hook = getattr(self.module, "add_day_terms", None)
        if hook is not None:
            hook(ctx)


def discover() -> list[Rule]:
    """Every public module in the rules folder, by (priority, name)."""
    importlib.invalidate_caches()
    found = []
    for info in pkgutil.iter_modules(rules_package.__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{rules_package.__name__}.{info.name}")
        found.append(
            Rule(
                name=str(getattr(module, "NAME", info.name)),
                priority=int(getattr(module, "PRIORITY", DEFAULT_PRIORITY)),
                module=module,
            )
        )
    return sorted(found, key=lambda r: (r.priority, r.name))
