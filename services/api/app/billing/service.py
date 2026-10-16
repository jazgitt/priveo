"""Payments by UPI: the 30-day cycle, the four statuses, "I've paid",
the admin's confirmation, invoices, and the daily jobs a scheduler will call."""

import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.config import MoneySettings
from app.billing.models import (
    PAYMENT_STATUSES,
    Invoice,
    MoneyAlert,
    Payment,
    PaymentEvent,
    SubscriptionEvent,
)
from app.billing.schemas import (
    AdminPaymentIn,
    AdminPaymentOut,
    InvoiceOut,
    PayInstructions,
    PaymentAlertOut,
    PaymentDetail,
    PaymentOut,
    SubscriptionView,
)
from app.changes.access import parse_id
from app.changes.cycle import cycle_window, paused_days, plan_expires_on, shift_days
from app.changes.rules import Clock, show_date, today_of
from app.customers.models import Customer, Subscription, Vehicle
from app.customers.service import show_registration, show_time
from app.directory import lookup
from app.directory.models import Plan, Society
from app.notifications import emit  # notify hook
from app.platform.config import get_settings
from app.platform.db import utcnow
from app.platform.errors import ApiError


def customer_name(c: Customer) -> str:
    return f"{c.first_name} {c.last_name}".strip()


def vehicle_label(v: Vehicle | None) -> str:
    if v is None:
        return ""
    return f"{v.model} {show_registration(v.registration)}".strip()


@dataclass
class OverdueReport:
    marked_overdue: int = 0
    inactivated: list[uuid.UUID] = field(default_factory=list)


class BillingService:
    def __init__(self, db: Session, now_fn: Clock, settings: MoneySettings):
        self._db = db
        self._now = now_fn
        self._settings = settings

    # ADM-SET: billing rules the admin can change (`billing.*`).
    @property
    def _cycle_days(self) -> int:  # SUB-01
        return lookup.setting(self._db, "billing.cycle_days")

    @property
    def _pay_ahead(self) -> int:  # ADM-PAY-06, SUB-09
        return lookup.setting(self._db, "billing.pay_ahead_days")

    @property
    def _inactive_after(self) -> int:  # SUB-11, ADM-SUB-03
        return lookup.setting(self._db, "billing.inactive_after_days")

    # --- output ------------------------------------------------------------

    def _invoices(self, payment_ids: list[uuid.UUID]) -> dict[uuid.UUID, Invoice]:
        if not payment_ids:
            return {}
        rows = self._db.scalars(select(Invoice).where(Invoice.payment_id.in_(payment_ids)))
        return {i.payment_id: i for i in rows}

    def _out(self, p: Payment, invoice: Invoice | None) -> PaymentOut:
        return PaymentOut(
            id=str(p.id),
            kind=p.kind,
            description=p.description,
            amount_rupees=p.amount_rupees,
            status=p.status,
            due_date=p.due_date,
            cycle_start=p.cycle_start,
            cycle_end=p.cycle_end,
            vehicle_id=str(p.vehicle_id) if p.vehicle_id else None,
            received_on=p.received_at.astimezone(self._tz()).date() if p.received_at else None,
            invoice_number=invoice.number if invoice else None,
        )

    def _tz(self):
        return self._now().tzinfo

    def _outs(self, rows: list[Payment]) -> list[PaymentOut]:
        inv = self._invoices([p.id for p in rows])
        return [self._out(p, inv.get(p.id)) for p in rows]

    def instructions(self, p: Payment) -> PayInstructions:
        upi_id = lookup.setting(self._db, "payment.upi_id")
        payee = lookup.setting(self._db, "payment.upi_payee_name")
        uri = (
            f"upi://pay?pa={quote(upi_id)}&pn={quote(payee)}"
            f"&am={p.amount_rupees}&cu=INR&tn={quote(p.description)}"
        )
        return PayInstructions(
            amount_rupees=p.amount_rupees,
            upi_id=upi_id,
            payee_name=payee,
            qr_url=lookup.setting(self._db, "payment.upi_qr_url") or None,
            upi_uri=uri,
            note="Pay from any UPI app, then tap I've paid.",
        )

    # --- events ------------------------------------------------------------

    def _event(
        self, p: Payment, old: str | None, new: str, by: uuid.UUID | None, note: str = ""
    ) -> None:
        self._db.add(
            PaymentEvent(payment_id=p.id, from_status=old, to_status=new, by_login_id=by, note=note)
        )
        if by:
            from app.directory.service import audit

            audit(self._db, by, "payment", p.id, "status", {"from": old, "to": new, "note": note})

    def _alert(
        self,
        kind: str,
        message: str,
        payment: Payment | None = None,
        sub_id: uuid.UUID | None = None,
    ) -> None:
        self._db.add(
            MoneyAlert(
                kind=kind,
                message=message,
                payment_id=payment.id if payment else None,
                subscription_id=sub_id,
            )
        )
        emit.admin_push(self._db, "Payment alert", message)  # notify hook

    # --- the customer ------------------------------------------------------

    def effective_status(self, sub: Subscription, vehicle: Vehicle, today: date) -> str:
        if sub.status == "Active" and today in paused_days(self._db, vehicle.id):
            return "Paused"  # PAUSE-04
        return sub.status

    def _unpaid_plan_payment(self, sub: Subscription) -> Payment | None:
        return self._db.scalar(
            select(Payment)
            .where(
                Payment.subscription_id == sub.id,
                Payment.kind == "Plan",
                Payment.status.in_(("Due", "Over due")),
                Payment.voided_at.is_(None),
            )
            .order_by(Payment.due_date)
        )

    def subscription_view(
        self, customer: Customer, vehicle: Vehicle, sub: Subscription | None
    ) -> SubscriptionView:
        if sub is None:
            raise ApiError("no_subscription", "This vehicle has no subscription.", 404)
        today = today_of(self._now())
        start, renewal = cycle_window(
            sub.first_service_date, shift_days(self._db, vehicle.id), today, self._cycle_days
        )
        plan = self._db.get(Plan, sub.plan_id) if sub.plan_id else None
        society = self._db.get(Society, vehicle.society_id or customer.society_id)
        latest = self._db.scalar(
            select(Payment)
            .where(
                Payment.subscription_id == sub.id,
                Payment.kind == "Plan",
                Payment.voided_at.is_(None),
            )
            .order_by(Payment.due_date.desc(), Payment.created_at.desc())
        )
        status = self.effective_status(sub, vehicle, today)
        expires_on = plan_expires_on(self._db, sub, today)
        payable = sub.status in ("Active",) and (
            self._unpaid_plan_payment(sub) is not None
            or (
                (renewal - today).days <= self._pay_ahead
                and (latest is None or latest.cycle_start != renewal)
            )
        )
        return SubscriptionView(
            vehicle_id=str(vehicle.id),
            subscription_id=str(sub.id),
            plan_name=plan.name if plan else None,
            plan_code=plan.code if plan else None,
            plan_list_price_rupees=plan.list_price_rupees if plan else None,
            plan_inclusions=list(plan.inclusions or []) if plan else [],
            vehicle=vehicle.model,
            registration=show_registration(vehicle.registration),
            society=society.name if society else "",
            status=status,
            monthly_price_rupees=sub.monthly_price_rupees,
            payment_method="UPI",
            cutoff_time=sub.cutoff_time.strftime("%H:%M") if sub.cutoff_time else None,
            interior_day=sub.interior_day,
            start_date=sub.first_service_date,
            cycle_start=start,
            renewal_date=renewal,
            expires_on=expires_on,
            cycle_days=self._cycle_days,
            days_left=max(0, (expires_on - today).days + 1),
            latest_payment=self._outs([latest])[0] if latest else None,
            can_pay_next=payable,
        )

    def history(self, customer: Customer, vehicle: Vehicle) -> list[PaymentOut]:
        """Newest first (SUB-06). Includes the vehicle's add-on payments."""
        rows = self._db.scalars(
            select(Payment)
            .where(
                Payment.customer_id == customer.id,
                Payment.vehicle_id == vehicle.id,
                Payment.voided_at.is_(None),
            )
            .order_by(Payment.due_date.desc(), Payment.created_at.desc())
        ).all()
        return self._outs(list(rows))

    def _own_payment(self, customer: Customer, payment_id: str) -> Payment:
        p = self._db.get(Payment, parse_id(payment_id, "payment"))
        if p is None or p.customer_id != customer.id or p.voided_at is not None:
            raise ApiError("not_found", "That payment was not found.", 404)
        return p

    def detail(self, customer: Customer, payment_id: str) -> PaymentDetail:
        p = self._own_payment(customer, payment_id)
        return self._detail(p)

    def _detail(self, p: Payment) -> PaymentDetail:
        vehicle = self._db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
        sub = self._db.get(Subscription, p.subscription_id) if p.subscription_id else None
        return PaymentDetail(payment=self._outs([p])[0], instructions=self.instructions(p),
                             vehicle=(f"{show_registration(vehicle.registration)} · "
                                      f"{vehicle.make} {vehicle.model} {vehicle.variant}".strip()
                                      if vehicle else ""),
                             service_details={"service": p.description,
                                              "cutoff_time": show_time(sub.cutoff_time) if sub else None,
                                              "interior_day": sub.interior_day if sub else None})

    def mark_paid(self, customer: Customer, payment_id: str) -> PaymentDetail:
        """ "I've paid" (PAY-06): the status becomes Initiated and goes to the admin."""
        p = self._own_payment(customer, payment_id)
        if p.status == "Received":
            raise ApiError("already_received", "Priveo has received this payment already.", 409)
        if p.status != "Initiated":
            old = p.status
            p.status = "Initiated"
            p.initiated_at = utcnow()
            self._event(p, old, "Initiated", None, "Customer tapped I've paid")
            self._alert(
                "payment_initiated",
                f"{customer_name(customer)} marked {p.description} (Rs {p.amount_rupees}) as paid.",
                p,
            )
            self._db.commit()
        return self._detail(p)

    def ensure_next_payment(
        self, customer: Customer, vehicle: Vehicle, sub: Subscription | None
    ) -> PaymentDetail:
        """ "Pay for next month" from one week before the renewal date (SUB-09)."""
        if sub is None or sub.status != "Active":
            raise ApiError(
                "subscription_not_active", "Payments are for an active subscription.", 409
            )
        today = today_of(self._now())
        unpaid = self._unpaid_plan_payment(sub)
        if unpaid is not None:
            return self._detail(unpaid)
        _, renewal = cycle_window(
            sub.first_service_date, shift_days(self._db, vehicle.id), today, self._cycle_days
        )
        if (renewal - today).days > self._pay_ahead:
            opens = renewal - timedelta(days=self._pay_ahead)
            raise ApiError("too_early", f"You can pay from {show_date(opens)}.", 409)
        p = self._cycle_payment(sub, vehicle, renewal)
        self._db.commit()
        return self._detail(p)

    def _cycle_payment(self, sub: Subscription, vehicle: Vehicle, renewal: date) -> Payment:
        found = self._db.scalar(
            select(Payment).where(Payment.subscription_id == sub.id, Payment.cycle_start == renewal)
        )
        if found is not None:
            return found
        p = Payment(
            customer_id=vehicle.customer_id,
            vehicle_id=vehicle.id,
            subscription_id=sub.id,
            kind="Plan",
            description=f"Plan {show_date(renewal)} to "
            f"{show_date(renewal + timedelta(days=self._cycle_days - 1))}",
            amount_rupees=(
                self._db.get(Plan, sub.pending_plan_id).monthly_price_rupees
                if sub.pending_plan_id and sub.pending_from and renewal >= sub.pending_from
                else sub.monthly_price_rupees
            ),
            status="Due",
            due_date=renewal,
            cycle_start=renewal,
            cycle_end=renewal + timedelta(days=self._cycle_days),
        )
        self._db.add(p)
        self._db.flush()
        self._event(p, None, "Due", None, "Created for the next cycle")
        return p

    def open_addon_payment(
        self, customer: Customer, vehicle: Vehicle, description: str, amount_rupees: int
    ) -> Payment:
        """An add-on payment is created Due on the day it is requested and
        becomes Over due the next day if unpaid (ADM-PAY-06, ADD-05). The caller commits."""
        p = Payment(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            kind="Add-on",
            description=description,
            amount_rupees=amount_rupees,
            status="Due",
            due_date=today_of(self._now()),
        )
        self._db.add(p)
        self._db.flush()
        self._event(p, None, "Due", None, "Add-on requested")
        return p

    def void_unpaid(self, payment_id: uuid.UUID | None) -> None:
        """A cancelled add-on is not charged (ADD-10). A Received payment is
        left for the admin to refund outside the app."""
        p = self._db.get(Payment, payment_id) if payment_id else None
        if p is not None and p.status != "Received" and p.voided_at is None:
            p.voided_at = utcnow()

    def invoice_for(self, customer: Customer, payment_id: str) -> InvoiceOut:
        p = self._own_payment(customer, payment_id)
        inv = self._db.scalar(select(Invoice).where(Invoice.payment_id == p.id))
        if inv is None:
            raise ApiError("no_invoice", "There is no invoice for this payment yet.", 404)
        return self._invoice_out(inv)

    def _invoice_out(self, inv: Invoice) -> InvoiceOut:
        seller = inv.seller_details or self._seller_details()
        return InvoiceOut(
            number=inv.number,
            issued_on=inv.issued_at.astimezone(self._tz()).date(),
            amount_rupees=inv.amount_rupees,
            description=inv.description,
            customer_name=inv.customer_name,
            vehicle=inv.vehicle_label,
            gst_included=True,
            seller_name=seller["seller_name"],
            seller_address=seller["seller_address"],
            seller_gstin=seller["seller_gstin"],
            tax_details=inv.tax_details,
        )

    def _seller_details(self) -> dict[str, str]:
        return {name: lookup.setting(self._db, f"invoice.{name}")
                for name in ("seller_name", "seller_address", "seller_gstin")}

    def _tax_details(self, amount_rupees: int) -> dict:
        from app.billing.tax import included_gst
        tax = included_gst(amount_rupees, self._settings.gst_rate_percent, self._settings.gst_mode)
        tax["mock_configuration"] = self._settings.gst_configuration_mock
        return tax

    @staticmethod
    def _seller_ready(seller: dict[str, str]) -> bool:
        return all(seller.get(key, "").strip() and "placeholder" not in seller[key].lower()
                   for key in ("seller_name", "seller_address", "seller_gstin")) and bool(
            re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", seller["seller_gstin"])
        )

    def invoice_pdf(self, payment_id: str, customer: Customer | None = None) -> tuple[str, bytes]:
        payment = self._own_payment(customer, payment_id) if customer else self._payment(payment_id)
        inv = self._db.scalar(select(Invoice).where(Invoice.payment_id == payment.id))
        if inv is None:
            raise ApiError("no_invoice", "The admin has not issued this invoice yet.", 404)
        invoice = self._invoice_out(inv)
        preview = not self._seller_ready(invoice.model_dump()) or bool(
            inv.tax_details and inv.tax_details.get("mock_configuration"))
        if preview and get_settings().environment != "dev":
            raise ApiError("invoice_settings_incomplete",
                           "Ask Priveo to configure the invoice supplier details.", 409)
        from app.billing.pdf import render_invoice
        filename = re.sub(r"[^A-Za-z0-9_.-]", "_", inv.number) + ".pdf"
        return filename, render_invoice(
            invoice, preview=preview, legacy=inv.seller_details is None
        )

    # --- the admin ---------------------------------------------------------

    def _admin_out(self, rows: list[Payment]) -> list[AdminPaymentOut]:
        base = self._outs(rows)
        out = []
        for p, b in zip(rows, base, strict=True):
            c = self._db.get(Customer, p.customer_id)
            v = self._db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
            society = self._db.get(Society, (v.society_id if v else None) or c.society_id)
            out.append(
                AdminPaymentOut(
                    **b.model_dump(),
                    customer_name=customer_name(c),
                    flat=c.flat,
                    society=society.name if society else "",
                    vehicle=vehicle_label(v),
                    initiated_at=p.initiated_at,
                )
            )
        return out

    def list_payments(
        self,
        *,
        status: str | None = None,
        kind: str | None = None,
        customer_id: str | None = None,
        vehicle_id: str | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        limit: int = 100,
        offset: int = 0,
        society: str | None = None,
    ) -> list[AdminPaymentOut]:
        q = select(Payment).where(Payment.voided_at.is_(None))
        if status:
            q = q.where(Payment.status == status)
        if kind:
            q = q.where(Payment.kind == kind)
        if customer_id:
            q = q.where(Payment.customer_id == parse_id(customer_id, "customer"))
        if vehicle_id:
            q = q.where(Payment.vehicle_id == parse_id(vehicle_id, "vehicle"))
        if due_before:
            q = q.where(Payment.due_date <= due_before)
        if due_after:
            q = q.where(Payment.due_date >= due_after)
        if society:
            q = q.join(Customer, Payment.customer_id == Customer.id).outerjoin(
                Vehicle, Payment.vehicle_id == Vehicle.id).join(
                Society, Society.id == func.coalesce(Vehicle.society_id, Customer.society_id)
            ).where(Society.name == society)
        rows = self._db.scalars(q.order_by(Payment.due_date, Payment.created_at, Payment.id)
                               .limit(limit).offset(offset)).all()
        return self._admin_out(list(rows))

    def _payment(self, payment_id: str) -> Payment:
        p = self._db.get(Payment, parse_id(payment_id, "payment"))
        if p is None or p.voided_at is not None:
            raise ApiError("not_found", "That payment was not found.", 404)
        return p

    def set_status(
        self, payment_id: str, status: str, admin_id: uuid.UUID, note: str = ""
    ) -> AdminPaymentOut:
        """Any status to any status (ADM-PAY-02, ADM-PAY-07). Audited (ADM-PAY-05)."""
        if status not in PAYMENT_STATUSES:
            raise ApiError(
                "validation_failed",
                "Choose Due, Over due, Initiated or Received.",
                422,
                {"status": "invalid"},
            )
        p = self._payment(payment_id)
        if p.status != status:
            self._apply(p, status, admin_id, note)
            self._db.commit()
        return self._admin_out([p])[0]

    def _apply(self, p: Payment, status: str, admin_id: uuid.UUID, note: str) -> None:
        old, now = p.status, self._now().astimezone(UTC)
        p.status = status
        if status == "Received":
            p.received_at, p.confirmed_by = now, admin_id
        else:
            p.received_at = None
            p.confirmed_by = None
        if status == "Initiated":
            p.initiated_at = p.initiated_at or now
        if status == "Over due":
            # The 7 days to Inactive start again from the admin's decision.
            p.overdue_since = today_of(self._now())
        elif status in ("Due", "Initiated"):
            p.overdue_since = None
        self._event(p, old, status, admin_id, note)

    def confirm(self, payment_id: str, admin_id: uuid.UUID) -> AdminPaymentOut:
        """PAY-08, ADM-PAY-03."""
        return self.set_status(payment_id, "Received", admin_id, "Confirmed")

    def reject(self, payment_id: str, admin_id: uuid.UUID) -> AdminPaymentOut:
        """The money did not arrive: back to Due, or Over due when the date has passed."""
        p = self._payment(payment_id)
        today = today_of(self._now())
        return self.set_status(
            payment_id, "Over due" if p.due_date < today else "Due", admin_id, "Rejected"
        )

    def create_payment(self, body: AdminPaymentIn, admin_id: uuid.UUID) -> AdminPaymentOut:
        if body.status not in PAYMENT_STATUSES or body.kind not in ("Plan", "Add-on"):
            raise ApiError("validation_failed", "Check the status and type.", 422)
        if body.amount_rupees <= 0:
            raise ApiError(
                "validation_failed",
                "The amount must be more than zero.",
                422,
                {"amount_rupees": "invalid"},
            )
        vehicle = self._db.get(Vehicle, parse_id(body.vehicle_id, "vehicle"))
        if vehicle is None:
            raise ApiError("not_found", "That vehicle was not found.", 404)
        sub = self._db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
        cycle_start = None
        if body.kind == "Plan":
            if sub is None:
                raise ApiError("no_subscription", "This vehicle has no subscription.", 404)
            cycle_start = body.cycle_start or body.due_date
            if self._db.scalar(
                select(Payment).where(
                    Payment.subscription_id == sub.id, Payment.cycle_start == cycle_start
                )
            ):
                raise ApiError("payment_exists", "That cycle has a payment already.", 409)
        p = Payment(
            customer_id=vehicle.customer_id,
            vehicle_id=vehicle.id,
            subscription_id=sub.id if sub else None,
            kind=body.kind,
            description=body.description
            or ("Plan payment" if body.kind == "Plan" else "Add-on payment"),
            amount_rupees=body.amount_rupees,
            status="Due",
            due_date=body.due_date,
            cycle_start=cycle_start,
            cycle_end=cycle_start + timedelta(days=self._cycle_days) if cycle_start else None,
        )
        self._db.add(p)
        self._db.flush()
        self._event(p, None, "Due", admin_id, "Created by the admin")
        if body.status != "Due":
            self._apply(p, body.status, admin_id, "Recorded by the admin")
        self._db.commit()
        return self._admin_out([p])[0]

    def issue_invoice(self, payment_id: str, admin_id: uuid.UUID) -> InvoiceOut:
        """ADM-PAY-08, ADM-PAY-09. Only for a Received payment."""
        p = self._payment(payment_id)
        if p.status != "Received":
            raise ApiError("not_received", "An invoice is made once the payment is Received.", 409)
        existing = self._db.scalar(select(Invoice).where(Invoice.payment_id == p.id))
        if existing is not None:
            return self._invoice_out(existing)
        c = self._db.get(Customer, p.customer_id)
        digits = re.sub(r"\D", "0", (c.mobile or "")[-4:].rjust(4, "0"))
        now = self._now()
        while True:
            number = f"PRV{now:%m%y}{digits}{random.randint(0, 9999):04d}"
            if not self._db.scalar(select(Invoice).where(Invoice.number == number)):
                break
        inv = Invoice(
            payment_id=p.id,
            number=number,
            issued_by=admin_id,
            amount_rupees=p.amount_rupees,
            customer_name=customer_name(c),
            vehicle_label=vehicle_label(self._db.get(Vehicle, p.vehicle_id))
            if p.vehicle_id
            else "",
            description=p.description,
            issued_at=now,
            seller_details=self._seller_details(),
            tax_details=self._tax_details(p.amount_rupees),
        )
        self._db.add(inv)
        self._db.commit()
        return self._invoice_out(inv)

    def alerts(self, unread_only: bool = False) -> list[PaymentAlertOut]:
        q = select(MoneyAlert).order_by(MoneyAlert.created_at.desc()).limit(100)
        if unread_only:
            q = q.where(MoneyAlert.read_at.is_(None))
        return [
            PaymentAlertOut(
                id=str(a.id),
                kind=a.kind,
                message=a.message,
                payment_id=str(a.payment_id) if a.payment_id else None,
                created_at=a.created_at,
                read=a.read_at is not None,
            )
            for a in self._db.scalars(q)
        ]

    def mark_alert_read(self, alert_id: str) -> None:
        a = self._db.get(MoneyAlert, parse_id(alert_id, "alert"))
        if a is None:
            raise ApiError("not_found", "That alert was not found.", 404)
        if a.read_at is None:
            a.read_at = utcnow()
            self._db.commit()

    def set_subscription_status(
        self,
        subscription_id: str,
        status: str,
        reason: str,
        first_service_date: date | None,
        admin_id: uuid.UUID,
    ) -> Subscription:
        """ADM-SUB-01, ADM-SUB-02, ADM-SUB-04, ADM-SUB-05."""
        sub = self._db.scalar(select(Subscription).where(
            Subscription.id == parse_id(subscription_id, "subscription")
        ).with_for_update())
        if sub is None:
            raise ApiError("not_found", "That subscription was not found.", 404)
        old = sub.status
        reactivated = self._db.scalar(select(SubscriptionEvent.id).where(
            SubscriptionEvent.subscription_id == sub.id,
            SubscriptionEvent.from_status == "Inactive",
            SubscriptionEvent.to_status == "Activating",
        ).limit(1)) is not None
        allowed = {
            "Inactive": old != "Inactive",
            "Activating": old == "Inactive",  # reactivate (ADM-SUB-04)
            "Active": old == "Activating",
        }
        if not allowed.get(status, False):
            raise ApiError(
                "invalid_transition", f"A subscription cannot go from {old} to {status}.", 409
            )
        if status == "Active" and reactivated:
            if first_service_date is None:
                raise ApiError("validation_failed", "Set the new first service date.", 422,
                               {"first_service_date": "Choose the new first service date."})
            if self._db.scalar(select(Payment.id).where(
                Payment.subscription_id == sub.id, Payment.cycle_start == first_service_date,
            )) is not None:
                raise ApiError("cycle_exists", "A payment already exists for that cycle.", 409)
        sub.status = status
        from app.directory.service import audit

        audit(
            self._db,
            admin_id,
            "subscription",
            sub.id,
            "status",
            {"from": old, "to": status, "reason": reason},
        )
        if first_service_date is not None:
            sub.first_service_date = first_service_date
            # The onboarding payment may precede the actual start of service.
            # Retain its receipt/status while anchoring the first cycle to service.
            initial = self._db.scalar(
                select(Payment).where(
                    Payment.subscription_id == sub.id,
                    Payment.description.like("First month of %"),
                    Payment.voided_at.is_(None),
                )
            )
            previously_active = self._db.scalar(
                select(SubscriptionEvent.id)
                .where(
                    SubscriptionEvent.subscription_id == sub.id,
                    SubscriptionEvent.to_status == "Active",
                )
                .limit(1)
            )
            if (status == "Active" and initial is not None
                    and previously_active is None and not reactivated):
                initial.cycle_start = first_service_date
                initial.cycle_end = first_service_date + timedelta(days=self._cycle_days)
                initial.due_date = first_service_date
        if status == "Active" and reactivated:
            self._cycle_payment(sub, self._db.get(Vehicle, sub.vehicle_id), first_service_date)
        self._db.add(
            SubscriptionEvent(
                subscription_id=sub.id,
                from_status=old,
                to_status=status,
                by_login_id=admin_id,
                reason=reason,
            )
        )
        self._db.commit()
        from app.scheduling.service import reconcile_vehicle

        reconcile_vehicle(self._db, sub.vehicle_id)
        return sub

    # --- the jobs (EventBridge, later) ---------------------------------------

    def generate_due_payments(self, now: datetime) -> int:
        """Creates each plan payment 7 days before the renewal date, Due by the
        renewal date (ADM-PAY-06). Pause edits move existing unpaid records
        transactionally. Returns how many were created."""
        today = today_of(now)
        for pending in self._db.scalars(
            select(Subscription).where(
                Subscription.pending_plan_id.is_not(None), Subscription.pending_from <= today
            )
        ):
            plan = self._db.get(Plan, pending.pending_plan_id)
            pending.plan_id, pending.monthly_price_rupees = plan.id, plan.monthly_price_rupees
            pending.pending_plan_id, pending.pending_from = None, None
            if not plan.includes_interior:
                pending.interior_day = None
        self._db.flush()
        created = 0
        subs = self._db.scalars(select(Subscription).where(Subscription.status == "Active"))
        for sub in list(subs):
            vehicle = self._db.get(Vehicle, sub.vehicle_id)
            _, renewal = cycle_window(
                sub.first_service_date, shift_days(self._db, vehicle.id), today, self._cycle_days
            )
            due = self._db.scalar(
                select(Payment)
                .where(
                    Payment.subscription_id == sub.id,
                    Payment.kind == "Plan",
                    Payment.status == "Due",
                    Payment.voided_at.is_(None),
                    Payment.cycle_start >= today - timedelta(days=self._cycle_days),
                )
                .order_by(Payment.cycle_start.desc())
            )
            if due is not None:
                # Pause edits synchronize these dates transactionally. Do not
                # move a first-cycle/reactivation Due record to a later cycle.
                continue
            if (renewal - today).days > self._pay_ahead:
                continue
            if self._db.scalar(
                select(Payment).where(
                    Payment.subscription_id == sub.id, Payment.cycle_start == renewal
                )
            ):
                continue
            self._cycle_payment(sub, vehicle, renewal)
            created += 1
        self._db.commit()
        return created

    def mark_overdue(self, now: datetime) -> OverdueReport:
        report = OverdueReport()
        today = today_of(now)
        due = self._db.scalars(
            select(Payment).where(
                Payment.status == "Due", Payment.due_date < today, Payment.voided_at.is_(None)
            )
        )
        for p in list(due):
            p.status = "Over due"
            p.overdue_since = p.due_date + timedelta(days=1)
            self._event(p, "Due", "Over due", None, "Due date passed")
            report.marked_overdue += 1
        self._db.flush()
        # An Over due add-on payment never makes a subscription Inactive.
        stale = self._db.scalars(
            select(Payment).where(
                Payment.kind == "Plan",
                Payment.status == "Over due",
                Payment.voided_at.is_(None),
                Payment.subscription_id.is_not(None),
                Payment.overdue_since <= today - timedelta(days=self._inactive_after),
            )
        )
        for p in list(stale):
            sub = self._db.get(Subscription, p.subscription_id)
            if sub is None or sub.status == "Inactive" or sub.id in report.inactivated:
                continue
            if (p.cycle_start or p.due_date) < sub.first_service_date:
                # Historical debt stays readable but belongs to the previous
                # activation, not the new cycle the admin has just started.
                continue
            old = sub.status
            sub.status = "Inactive"
            self._db.add(
                SubscriptionEvent(
                    subscription_id=sub.id,
                    from_status=old,
                    to_status="Inactive",
                    by_login_id=None,
                    reason="Plan payment over due for 7 days",
                )
            )
            c = self._db.get(Customer, p.customer_id)
            self._alert(
                "auto_inactive",
                f"{customer_name(c)}'s subscription is Inactive: the plan payment "
                f"has been over due for {self._inactive_after} days.",
                p,
                sub.id,
            )
            report.inactivated.append(sub.id)
        self._db.commit()
        from app.scheduling.service import reconcile_vehicle

        for subscription_id in report.inactivated:
            reconcile_vehicle(self._db, self._db.get(Subscription, subscription_id).vehicle_id)
        return report


def mark_overdue_and_inactive(
    now: datetime, db: Session | None = None, settings: MoneySettings | None = None
) -> OverdueReport:
    """The daily job (ADM-PAY-06, ADM-SUB-03, SUB-11). A Due payment past its
    date becomes Over due. A plan payment Over due for 7 days makes its
    subscription Inactive. Safe to run again. Without `db` it opens its own
    session on the configured database."""
    from app.billing.config import get_money_settings

    settings = settings or get_money_settings()
    if db is not None:
        return BillingService(db, lambda: now, settings).mark_overdue(now)
    from app.platform.db import get_engine

    with Session(get_engine(), expire_on_commit=False) as session:
        return BillingService(session, lambda: now, settings).mark_overdue(now)


def generate_due_payments(
    now: datetime, db: Session | None = None, settings: MoneySettings | None = None
) -> int:
    """The daily job that creates next cycle's Due payments (billing.generate_due)."""
    from app.billing.config import get_money_settings

    settings = settings or get_money_settings()
    if db is not None:
        return BillingService(db, lambda: now, settings).generate_due_payments(now)
    from app.platform.db import get_engine

    with Session(get_engine(), expire_on_commit=False) as session:
        return BillingService(session, lambda: now, settings).generate_due_payments(now)
