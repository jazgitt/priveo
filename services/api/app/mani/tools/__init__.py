"""Live read tools (Phase 1 step 7). Add each tool module here."""
from app.mani.contracts import Scrubber
from app.mani.tools.registry import ToolRegistry


def build_registry(scrubber: Scrubber | None = None) -> ToolRegistry:
    return ToolRegistry([], scrubber=scrubber)
