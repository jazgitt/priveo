"""Live read tools (Phase 1 step 7). Add each tool module here."""
from app.mani.contracts import Scrubber, Tool
from app.mani.tools.addons import AddonsSummary
from app.mani.tools.crew import CrewSummary
from app.mani.tools.operations import CapacityOutlook, OnTimeSummary, OperationsSummary
from app.mani.tools.payments import PaymentsSummary
from app.mani.tools.registry import ToolRegistry
from app.mani.tools.subscriptions import ScheduleChangesSummary, SubscriptionsSummary
from app.mani.tools.support import ComplaintsSummary, RatingsSummary


def all_tools() -> list[Tool]:
    return [
        SubscriptionsSummary(), ScheduleChangesSummary(), ComplaintsSummary(), RatingsSummary(),
        OperationsSummary(), OnTimeSummary(), CapacityOutlook(), AddonsSummary(),
        PaymentsSummary(), CrewSummary(),
    ]


def build_registry(scrubber: Scrubber | None = None) -> ToolRegistry:
    return ToolRegistry(all_tools(), scrubber=scrubber)
