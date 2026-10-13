import datetime as dt

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.billing.config import MoneySettings, get_money_settings
from app.billing.schemas import (
    AdminPaymentIn,
    AdminPaymentOut,
    InvoiceOut,
    PaymentAlertOut,
    PaymentDetail,
    PaymentOut,
    StatusIn,
    SubscriptionStatusIn,
    SubscriptionStatusOut,
    SubscriptionView,
)
from app.billing.service import BillingService
from app.changes.access import customer_of, owned_vehicle
from app.changes.rules import Clock, get_now
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role

customer = APIRouter(prefix="/v1/customer", tags=["billing"])
admin = APIRouter(prefix="/v1/admin", tags=["billing"])


def get_billing_service(
    db: Session = Depends(get_db),
    now: Clock = Depends(get_now),
    settings: MoneySettings = Depends(get_money_settings),
) -> BillingService:
    return BillingService(db, now, settings)


# --- the customer -------------------------------------------------------------


@customer.get("/vehicles/{vehicle_id}/subscription", response_model=SubscriptionView)
def my_subscription(
    vehicle_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: BillingService = Depends(get_billing_service),
):
    c, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.subscription_view(c, vehicle, sub)


@customer.get("/vehicles/{vehicle_id}/payments", response_model=list[PaymentOut])
def billing_history(
    vehicle_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: BillingService = Depends(get_billing_service),
):
    c, vehicle, _ = owned_vehicle(db, user.id, vehicle_id)
    return svc.history(c, vehicle)


@customer.post("/vehicles/{vehicle_id}/payments/next", response_model=PaymentDetail)
def pay_for_next_month(
    vehicle_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: BillingService = Depends(get_billing_service),
):
    c, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.ensure_next_payment(c, vehicle, sub)


@customer.get("/payments/{payment_id}", response_model=PaymentDetail)
def payment_detail(
    payment_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.detail(customer_of(db, user.id), payment_id)


@customer.post("/payments/{payment_id}/paid", response_model=PaymentDetail)
def ive_paid(
    payment_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.mark_paid(customer_of(db, user.id), payment_id)


@customer.get("/payments/{payment_id}/invoice", response_model=InvoiceOut)
def my_invoice(
    payment_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.invoice_for(customer_of(db, user.id), payment_id)


def pdf_response(filename: str, content: bytes) -> Response:
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


@customer.get("/payments/{payment_id}/invoice.pdf", response_class=Response,
              responses={200: {"content": {"application/pdf": {"schema": {
                  "type": "string", "format": "binary"}}}}})
def my_invoice_pdf(payment_id: str, user: User = Depends(require_role("customer")),
                   db: Session = Depends(get_db),
                   svc: BillingService = Depends(get_billing_service)):
    filename, content = svc.invoice_pdf(payment_id, customer_of(db, user.id))
    return pdf_response(filename, content)


# --- the admin ----------------------------------------------------------------


@admin.get("/payments", response_model=list[AdminPaymentOut])
def list_payments(
    society: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    customer_id: str | None = None,
    vehicle_id: str | None = None,
    due_before: dt.date | None = None,
    due_after: dt.date | None = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.list_payments(
        society=society,
        status=status,
        kind=kind,
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        due_before=due_before,
        due_after=due_after,
        limit=min(max(limit, 1), 500),
        offset=max(offset, 0),
    )


@admin.post("/payments", response_model=AdminPaymentOut, status_code=201)
def create_payment(
    body: AdminPaymentIn,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.create_payment(body, user.id)


@admin.get("/payments/{payment_id}", response_model=AdminPaymentOut)
def admin_payment_detail(
    payment_id: str,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc._admin_out([svc._payment(payment_id)])[0]


@admin.put("/payments/{payment_id}/status", response_model=AdminPaymentOut)
def set_payment_status(
    payment_id: str,
    body: StatusIn,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.set_status(payment_id, body.status, user.id)


@admin.post("/payments/{payment_id}/confirm", response_model=AdminPaymentOut)
def confirm_payment(
    payment_id: str,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.confirm(payment_id, user.id)


@admin.post("/payments/{payment_id}/reject", response_model=AdminPaymentOut)
def reject_payment(
    payment_id: str,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.reject(payment_id, user.id)


@admin.post("/payments/{payment_id}/invoice", response_model=InvoiceOut)
def issue_invoice(
    payment_id: str,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.issue_invoice(payment_id, user.id)


@admin.get("/payment-alerts", response_model=list[PaymentAlertOut])
def alerts(
    unread_only: bool = False,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    return svc.alerts(unread_only)


@admin.get("/payments/{payment_id}/invoice.pdf", response_class=Response,
           responses={200: {"content": {"application/pdf": {"schema": {
               "type": "string", "format": "binary"}}}}})
def admin_invoice_pdf(payment_id: str, user: User = Depends(require_role("admin")),
                      svc: BillingService = Depends(get_billing_service)):
    filename, content = svc.invoice_pdf(payment_id)
    return pdf_response(filename, content)


@admin.post("/payment-alerts/{alert_id}/read", status_code=204)
def read_alert(
    alert_id: str,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    svc.mark_alert_read(alert_id)
    return Response(status_code=204)


@admin.put("/subscriptions/{subscription_id}/status", response_model=SubscriptionStatusOut)
def set_subscription_status(
    subscription_id: str,
    body: SubscriptionStatusIn,
    user: User = Depends(require_role("admin")),
    svc: BillingService = Depends(get_billing_service),
):
    sub = svc.set_subscription_status(
        subscription_id, body.status, body.reason, body.first_service_date, user.id
    )
    return SubscriptionStatusOut(subscription_id=str(sub.id), status=sub.status)
