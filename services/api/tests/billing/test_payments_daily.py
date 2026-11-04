"""The one daily payments job at 2:00 IST (ADM-PAY-14, PAY-19) and the schedule."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.billing.config import get_money_settings
from app.billing.models import MoneyAlert, Payment
from app.notifications import cron
from app.platform.clock import IST
from tests.billing.test_billing import admin_payment

VERCEL = Path(__file__).resolve().parents[2] / "vercel.json"


def run(m, now):
    return cron._payments_daily(m.db, now, get_money_settings())


def cycles(m):
    m.db.expire_all()
    return sorted(r.cycle_start.isoformat() for r in m.db.scalars(
        select(Payment).where(Payment.subscription_id == m.subscription_id)))


def test_vercel_json_has_the_one_daily_job_and_not_the_old_two():
    crons = {c["path"].rsplit("/", 1)[1]: c["schedule"]
             for c in json.loads(VERCEL.read_text())["crons"]}
    assert crons["payments-daily"] == "30 20 * * *"  # 2:00 IST
    assert "payments-generate" not in crons and "payments-overdue" not in crons
    assert crons["renewal-reminders"] == "30 4 * * *"  # reminders stay at 10:00 IST


def test_the_old_job_names_stay_registered_as_aliases():
    for name in ("payments-daily", "payments-generate", "payments-overdue", "renewal-reminders"):
        assert name in cron.JOBS


def test_the_day_changes_at_2_ist_for_the_new_cycle(money):
    m = money  # first cycle 1-Oct-26 to 30-Oct-26
    run(m, datetime(2026, 10, 31, 1, 59, tzinfo=IST))  # still 30 Oct
    assert cycles(m) == ["2026-10-01"]
    run(m, datetime(2026, 10, 31, 2, 0, tzinfo=IST))  # 31 Oct: the next cycle starts
    assert cycles(m) == ["2026-10-01", "2026-10-31"]
    run(m, datetime(2026, 10, 31, 2, 0, tzinfo=IST))  # run again: nothing new
    assert cycles(m) == ["2026-10-01", "2026-10-31"]


def test_the_day_changes_at_2_ist_for_over_due(money):
    m = money
    p = admin_payment(m, cycle_start="2026-10-01")  # due 30-Oct-26
    row = m.db.get(Payment, uuid.UUID(p["id"]))
    assert run(m, datetime(2026, 10, 31, 1, 59, tzinfo=IST))["marked_overdue"] == 0  # due today
    m.db.refresh(row)
    assert row.overdue_since is None
    assert run(m, datetime(2026, 10, 31, 2, 0, tzinfo=IST))["marked_overdue"] == 1
    m.db.refresh(row)
    assert row.overdue_since is not None


def test_a_customer_onboarded_at_1_am_counts_as_the_day_before():
    from app.changes.rules import payment_day_of

    assert payment_day_of(datetime(2026, 11, 5, 1, 0, tzinfo=IST)).isoformat() == "2026-11-04"
    assert payment_day_of(datetime(2026, 11, 5, 1, 59, tzinfo=IST)).isoformat() == "2026-11-04"
    assert payment_day_of(datetime(2026, 11, 5, 2, 0, tzinfo=IST)).isoformat() == "2026-11-05"


def test_the_job_makes_payments_first_then_marks_overdue_and_inactive(money, monkeypatch):
    order = []
    real_generate, real_overdue = cron._payments_generate, cron._payments_overdue
    monkeypatch.setattr(cron, "_payments_generate",
                        lambda *a: (order.append("generate"), real_generate(*a))[1])
    monkeypatch.setattr(cron, "_payments_overdue",
                        lambda *a: (order.append("overdue"), real_overdue(*a))[1])
    result = run(money, datetime(2026, 10, 31, 2, 0, tzinfo=IST))
    assert order == ["generate", "overdue"]
    assert {"created", "marked_overdue", "inactivated"} <= set(result)


def test_auto_inactive_runs_in_the_daily_job_with_its_alert(money):
    m = money
    admin_payment(m, cycle_start="2026-10-01")  # due 30-Oct-26
    # Over due for 7 days (1 to 7 Nov): still Active. The next day: Inactive.
    first = run(m, datetime(2026, 11, 6, 2, 0, tzinfo=IST))
    assert first["inactivated"] == 0 and m.subscription().status == "Active"
    second = run(m, datetime(2026, 11, 7, 2, 0, tzinfo=IST))
    assert second["inactivated"] == 1
    assert m.subscription().status == "Inactive"
    assert [a.kind for a in m.db.scalars(select(MoneyAlert))] == ["auto_inactive"]
    assert run(m, datetime(2026, 11, 7, 2, 0, tzinfo=IST))["inactivated"] == 0


def test_the_job_passes_the_payment_day_and_leaves_the_clock_real(money):
    from datetime import date

    from app.billing import service as billing_service

    m = money  # first cycle 1-Oct-26 to 30-Oct-26
    now = datetime(2026, 10, 31, 2, 0, tzinfo=IST)
    seen = {}
    real = billing_service.BillingService.generate_due_payments

    def spy(self, at, today=None):
        seen["clock"], seen["today"] = self._now(), today
        return real(self, at, today)

    billing_service.BillingService.generate_due_payments = spy
    try:
        run(m, now)
    finally:
        billing_service.BillingService.generate_due_payments = real
    assert seen["clock"] == now  # timestamps stay real
    assert seen["today"] == date(2026, 10, 31)
