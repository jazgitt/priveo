"""The set of live read tools Mani may call. Each tool lives in its own module and is
added in `tools/__init__.py:build_registry`. The registry is the only way a tool runs."""
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.mani.contracts import Scrubber, Tool, ToolError, ToolResult, ToolSpec


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] = (), *, scrubber: Scrubber | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._scrubber = scrubber
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError(f"Tool {tool.spec.name!r} is registered twice.")
        self._tools[tool.spec.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def run(self, db: Session, name: str, arguments: dict[str, Any], *, now: datetime) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"There is no tool called {name!r}.")
        result = tool.run(db, arguments, now=now)
        if self._scrubber is not None:
            # The last defence: nothing leaves a tool unscrubbed (D14).
            result = ToolResult(data=self._scrubber.scrub_data(result.data),
                                citation=result.citation,
                                summary=self._scrubber.scrub(result.summary).text)
        return result
