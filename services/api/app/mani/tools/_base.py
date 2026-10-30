"""Shared helpers for the live read tools: argument checks, Asia/Kolkata day and week
boundaries, and the base class. Nothing here touches the clock; `now` is always passed in."""
import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.directory.models import Society
from app.mani.contracts import Citation, ToolError, ToolResult, ToolSpec

IST = ZoneInfo("Asia/Kolkata")
MAX_ROWS = 25  # the longest list any tool returns; the data says when it cut a list
MAX_SPAN_DAYS = 400


class ReadTool:
    """A read-only tool. A subclass sets `spec` and `compute`; `run` does the shared work."""

    spec: ToolSpec
    title: str = ""

    def run(self, db: Session, arguments: dict[str, Any], *, now: datetime) -> ToolResult:
        if now.tzinfo is None:
            raise ToolError("The time must carry a timezone.")
        args = arguments or {}
        if not isinstance(args, dict):
            raise ToolError("The arguments must be an object.")
        allowed = self.spec.parameters.get("properties", {})
        unknown = sorted(set(args) - set(allowed))
        if unknown:
            raise ToolError(f"{self.spec.name} has no argument {unknown[0]!r}. "
                            f"Allowed: {', '.join(allowed) or 'none'}.")
        data, summary = self.compute(db, args, now.astimezone(UTC))
        citation = Citation(title=self.title or self.spec.name, kind="tool",
                            path=self.spec.name, as_of=now)
        return ToolResult(data=data, citation=citation, summary=summary)

    def compute(self, db: Session, args: dict[str, Any], now: datetime) -> tuple[Any, str]:
        raise NotImplementedError


def schema(properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties or {}, "additionalProperties": False}


# ---- Dates (Asia/Kolkata) ------------------------------------------------------------------


def today_ist(now: datetime) -> date:
    return now.astimezone(IST).date()


def ist_start(day: date) -> datetime:
    """The first instant of an IST day, as aware UTC."""
    return datetime.combine(day, time.min, tzinfo=IST).astimezone(UTC)


def ist_range(first: date, last: date) -> tuple[datetime, datetime]:
    """[start, end) in UTC for the IST days first..last, both included."""
    return ist_start(first), ist_start(last + timedelta(days=1))


def iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(IST).isoformat(timespec="minutes")
    return value.isoformat()


def hhmm(minute: int | None) -> str | None:
    return None if minute is None else f"{minute // 60:02d}:{minute % 60:02d}"


def first_of_month(day: date) -> date:
    return day.replace(day=1)


def add_months(first: date, months: int) -> date:
    index = first.year * 12 + (first.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def month_last_day(first: date) -> date:
    return add_months(first, 1) - timedelta(days=1)


def week_start(day: date, starts_on: str) -> date:
    """The first day of the week that holds `day`. Monday by default; Sunday on request."""
    back = day.weekday() if starts_on == "monday" else (day.weekday() + 1) % 7
    return day - timedelta(days=back)


# ---- Arguments -----------------------------------------------------------------------------

FROM_DATE = {"type": "string", "description": "First day of the period, YYYY-MM-DD (India time)."}
TO_DATE = {"type": "string", "description": "Last day of the period, YYYY-MM-DD, included."}
WEEK_START = {"type": "string", "enum": ["monday", "sunday"],
              "description": "Which day a week starts on. Default monday."}


def get_date(args: dict[str, Any], name: str, default: date | None = None) -> date | None:
    value = args.get(name)
    if value in (None, ""):
        return default
    try:
        if not isinstance(value, str):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise ToolError(f"{name} must be a date like 2026-10-30.") from None


def get_month(args: dict[str, Any], name: str, default: date) -> date:
    value = args.get(name)
    if value in (None, ""):
        return default
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ToolError(f"{name} must be a month like 2026-10.")
    return date(int(value[:4]), int(value[5:]), 1)


def get_period(args: dict[str, Any], default_first: date, default_last: date) -> tuple[date, date]:
    first = get_date(args, "from_date", default_first)
    last = get_date(args, "to_date", default_last)
    assert first is not None and last is not None
    if last < first:
        raise ToolError("to_date must not be before from_date.")
    if (last - first).days > MAX_SPAN_DAYS:
        raise ToolError(f"The period may be at most {MAX_SPAN_DAYS} days.")
    return first, last


def get_int(args: dict[str, Any], name: str, default: int, low: int, high: int) -> int:
    value = args.get(name)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ToolError(f"{name} must be a whole number from {low} to {high}.")
    return value


def get_bool(args: dict[str, Any], name: str, default: bool = False) -> bool:
    value = args.get(name)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ToolError(f"{name} must be true or false.")
    return value


def get_choice(args: dict[str, Any], name: str, choices: tuple[str, ...], default: str) -> str:
    value = args.get(name)
    if value is None:
        return default
    if value not in choices:
        raise ToolError(f"{name} must be one of: {', '.join(choices)}.")
    return value


def get_text(args: dict[str, Any], name: str, max_len: int = 80) -> str | None:
    value = args.get(name)
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > max_len:
        raise ToolError(f"{name} must be text of at most {max_len} characters.")
    return value.strip() or None


# ---- Small shared pieces -------------------------------------------------------------------


def capped(rows: list, limit: int = MAX_ROWS) -> dict[str, Any]:
    """A list cut to `limit`, with the full count so a cut is never silent."""
    return {"items": rows[:limit], "total": len(rows), "truncated": len(rows) > limit}


def pct(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def full_name(first: str | None, last: str | None) -> str:
    return f"{first or ''} {last or ''}".strip()


def find_societies(db: Session, text: str) -> list[tuple[Any, str]]:
    """Societies whose name holds `text`, ignoring case. Plain error when none do."""
    needle = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = db.execute(select(Society.id, Society.name)
                      .where(func.lower(Society.name).like(f"%{needle}%", escape="\\"))
                      .order_by(Society.name)).all()
    if not rows:
        raise ToolError(f"No society has a name like {text!r}.")
    return [(r.id, r.name) for r in rows]
