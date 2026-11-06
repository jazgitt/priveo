"""SCHS-48: the weekly summary as a file (SCHR-OUT-06). Read only.

A CSV built from the same figures the weekly summary endpoint gives
(`reports_weekly.weekly_summary`), so the file matches the screen. Dates are
`dd-Mon-yy`. CSV is the format (DERIVED: it opens in any spreadsheet and needs
no extra library)."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.changes.rules import show_date
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.scheduling.routes.reports_weekly import InteriorLine, WeeklySummary, weekly_summary

router = APIRouter(prefix="/v1/admin/scheduling/reports", tags=["scheduling"])


def _day(d: date | None) -> str:
    return "" if d is None else show_date(d)


def _interiors(out, title: str, lines: list[InteriorLine]) -> None:
    out.writerow([])
    out.writerow([title])
    out.writerow(["Car", "Service week", "Status", "Completed on", "Overdue days", "Catch-up"])
    for ln in lines:
        out.writerow([ln.registration, _day(ln.service_week_start), ln.status,
                      _day(ln.completed_on), ln.overdue_days, "Yes" if ln.catch_up else "No"])


def weekly_csv(summary: WeeklySummary) -> str:
    buffer = io.StringIO()
    out = csv.writer(buffer, lineterminator="\r\n")
    out.writerow(["Weekly summary", _day(summary.week_start), _day(summary.week_end)])
    out.writerow([])
    out.writerow(["Exteriors", "Due", "Completed", "Missed", "Open"])
    e = summary.exteriors
    out.writerow(["", e.due, e.completed, e.missed, e.open])
    out.writerow([])
    out.writerow(["Completions", "Weekday", "Weekend"])
    out.writerow(["", summary.completions.weekday, summary.completions.weekend])
    out.writerow([])
    out.writerow(["Carry-over", "Carried in", "Still owed"])
    out.writerow(["", summary.carry_over.carried_in, summary.carry_over.still_owed])
    out.writerow([])
    out.writerow(["Catch-up services", summary.catch_up_services])
    out.writerow(["Missed breaks", summary.missed_breaks])
    _interiors(out, "Interiors by service week", summary.interiors_by_service_week)
    _interiors(out, "Interiors completed in the week", summary.interiors_completed_in_week)
    return buffer.getvalue()


@router.get("/weekly/export")
def export_weekly(
    society_id: uuid.UUID,
    week_start: date,
    as_of: date | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    summary = weekly_summary(db, society_id, week_start, as_of)
    name = f"weekly-summary-{summary.week_start.isoformat()}.csv"
    return Response(
        content=weekly_csv(summary), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'})
