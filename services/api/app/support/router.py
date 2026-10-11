import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.support import alerts
from app.support.config import SupportSettings, get_support_settings
from app.support.notify import (
    EmailNotifier,
    LoggingEmailNotifier,
    LoggingPushNotifier,
    PushNotifier,
)
from app.support.schemas import (
    AdminComplaintDetail,
    AdminComplaintSummary,
    AlertList,
    AlertOut,
    CheckInCreate,
    CheckInOut,
    CheckInsReport,
    ComplaintCreate,
    ComplaintDetail,
    ComplaintSummary,
    CrewRatings,
    FeedbackAdmin,
    FeedbackCreate,
    FeedbackOut,
    MessageCreate,
    OptionAdmin,
    OptionCreate,
    OptionPatch,
    Options,
    PendingCheckIn,
    RatingCreate,
    RatingOut,
    RatingsReport,
    StatusChange,
    SupportContact,
)
from app.support.service import SupportService

customer = APIRouter(prefix="/v1/customer", tags=["support"])
crew = APIRouter(prefix="/v1/crew", tags=["support"])
admin = APIRouter(prefix="/v1/admin", tags=["support"])


def get_push_notifier() -> PushNotifier:
    return LoggingPushNotifier()


def get_email_notifier() -> EmailNotifier:
    return LoggingEmailNotifier()


def get_support_service(db: Session = Depends(get_db),
                        push: PushNotifier = Depends(get_push_notifier),
                        email: EmailNotifier = Depends(get_email_notifier)) -> SupportService:
    return SupportService(db, push, email)


# Customer -------------------------------------------------------------

@customer.get("/support/contact", response_model=SupportContact)
def contact(user: User = Depends(require_role("customer")),
            service: SupportService = Depends(get_support_service),
            settings: SupportSettings = Depends(get_support_settings)):
    """The helpline and WhatsApp numbers and hours (SUP-02 to SUP-04), and the
    count of complaints in progress (SUP-01)."""
    me = service.customer_for(user.id)
    return SupportContact(helpline=settings.support_helpline, whatsapp=settings.support_whatsapp,
                          hours=settings.support_hours,
                          complaints_in_progress=service.in_progress_count(me))


@customer.get("/support/options", response_model=Options)
def options(user: User = Depends(require_role("customer")),
            service: SupportService = Depends(get_support_service)):
    """The lists the forms use: issue categories (ISS-01), feedback categories
    (FDBK-06), positive tags (SVC-11), check-in categories (CHK-03)."""
    return service.options()


@customer.post("/complaints", response_model=ComplaintDetail, status_code=201)
def create_complaint(body: ComplaintCreate, user: User = Depends(require_role("customer")),
                     service: SupportService = Depends(get_support_service)):
    return service.create_complaint(service.customer_for(user.id), body.category,
                                    body.description, body.visit_id, body.photo_keys)


@customer.get("/complaints", response_model=list[ComplaintSummary])
def my_complaints(user: User = Depends(require_role("customer")),
                  service: SupportService = Depends(get_support_service)):
    return service.list_for_customer(service.customer_for(user.id))


@customer.get("/complaints/{complaint_id}", response_model=ComplaintDetail)
def my_complaint(complaint_id: uuid.UUID, user: User = Depends(require_role("customer")),
                 service: SupportService = Depends(get_support_service)):
    return service.detail_for_customer(service.customer_for(user.id), complaint_id)


@customer.post("/complaints/{complaint_id}/messages", response_model=ComplaintDetail)
def reply_to_complaint(complaint_id: uuid.UUID, body: MessageCreate,
                       user: User = Depends(require_role("customer")),
                       service: SupportService = Depends(get_support_service)):
    return service.customer_message(service.customer_for(user.id), complaint_id, body.note)


@customer.post("/feedback", response_model=FeedbackOut, status_code=201)
def give_feedback(body: FeedbackCreate, user: User = Depends(require_role("customer")),
                  service: SupportService = Depends(get_support_service)):
    row = service.give_feedback(service.customer_for(user.id), body.category, body.rating,
                                body.comment, body.testimonial_permission)
    return FeedbackOut(id=row.id, created_at=row.created_at)


@customer.put("/visits/{visit_id}/rating", response_model=RatingOut)
def rate_visit(visit_id: str, body: RatingCreate, user: User = Depends(require_role("customer")),
               service: SupportService = Depends(get_support_service)):
    """A general rating of the visit, with tags (SVC-07, SVC-11, SVC-12, SVC-14).
    Sending it again replaces the earlier rating."""
    return service.rate_visit(service.customer_for(user.id), visit_id, body.rating, body.tags,
                              body.comment, body.testimonial_permission)


@customer.get("/checkins/pending", response_model=list[PendingCheckIn])
def pending_checkins(user: User = Depends(require_role("customer")),
                     service: SupportService = Depends(get_support_service)):
    """Check-ins to give now, for the Home card (CHK-08)."""
    return service.pending_checkins(service.customer_for(user.id))


@customer.post("/checkins", response_model=CheckInOut, status_code=201)
def submit_checkin(body: CheckInCreate, user: User = Depends(require_role("customer")),
                   service: SupportService = Depends(get_support_service)):
    row = service.submit_checkin(service.customer_for(user.id), body.subscription_id,
                                 body.answers, body.comment)
    return CheckInOut(id=row.id, cycle_start=row.cycle_start)


# Crew -----------------------------------------------------------------

@crew.get("/ratings", response_model=CrewRatings)
def crew_ratings(user: User = Depends(require_role("crew")),
                 service: SupportService = Depends(get_support_service)):
    """General visit ratings of the last 30 days. No names, tags or comments."""
    return service.crew_ratings()


# Admin ----------------------------------------------------------------

@admin.get("/complaints", response_model=list[AdminComplaintSummary])
def admin_complaints(status: str | None = None, category: str | None = None,
                     user: User = Depends(require_role("admin")),
                     service: SupportService = Depends(get_support_service)):
    return service.list_for_admin(status, category)


@admin.get("/complaints/{complaint_id}", response_model=AdminComplaintDetail)
def admin_complaint(complaint_id: uuid.UUID, user: User = Depends(require_role("admin")),
                    service: SupportService = Depends(get_support_service)):
    return service.detail_for_admin(complaint_id)


@admin.post("/complaints/{complaint_id}/status", response_model=AdminComplaintDetail)
def admin_set_status(complaint_id: uuid.UUID, body: StatusChange,
                     user: User = Depends(require_role("admin")),
                     service: SupportService = Depends(get_support_service)):
    return service.admin_update(user.id, complaint_id, body.status, body.note)


@admin.post("/complaints/{complaint_id}/notes", response_model=AdminComplaintDetail)
def admin_add_note(complaint_id: uuid.UUID, body: MessageCreate,
                   user: User = Depends(require_role("admin")),
                   service: SupportService = Depends(get_support_service)):
    return service.admin_update(user.id, complaint_id, None, body.note)


@admin.get("/feedback", response_model=list[FeedbackAdmin])
def admin_feedback(category: str | None = None, rating: int | None = None,
                   user: User = Depends(require_role("admin")),
                   service: SupportService = Depends(get_support_service)):
    return service.feedback_for_admin(category, rating)


@admin.get("/ratings", response_model=RatingsReport)
def admin_ratings(user: User = Depends(require_role("admin")),
                  service: SupportService = Depends(get_support_service)):
    return service.ratings_for_admin()


@admin.get("/checkins", response_model=CheckInsReport)
def admin_checkins(user: User = Depends(require_role("admin")),
                   service: SupportService = Depends(get_support_service)):
    return service.checkins_for_admin()


@admin.get("/support/options", response_model=list[OptionAdmin])
def admin_options(user: User = Depends(require_role("admin")),
                  service: SupportService = Depends(get_support_service)):
    return service.all_options()


@admin.post("/support/options", response_model=OptionAdmin, status_code=201)
def admin_add_option(body: OptionCreate, user: User = Depends(require_role("admin")),
                     service: SupportService = Depends(get_support_service)):
    o = service.add_option(body.kind, body.name, body.description)
    return OptionAdmin(id=o.id, kind=o.kind, name=o.name, description=o.description,
                       sort_order=o.sort_order, active=o.active)


@admin.patch("/support/options/{option_id}", response_model=OptionAdmin)
def admin_patch_option(option_id: uuid.UUID, body: OptionPatch,
                       user: User = Depends(require_role("admin")),
                       service: SupportService = Depends(get_support_service)):
    o = service.patch_option(option_id, body.name, body.description, body.active,
                             body.sort_order)
    return OptionAdmin(id=o.id, kind=o.kind, name=o.name, description=o.description,
                       sort_order=o.sort_order, active=o.active)


def _alert_out(a) -> AlertOut:
    return AlertOut(id=a.id, kind=a.kind, title=a.title, body=a.body, ref_type=a.ref_type,
                    ref_id=a.ref_id, created_at=a.created_at, read=a.read_at is not None)


@admin.get("/alerts", response_model=AlertList)
def admin_alerts(unread_only: bool = False, user: User = Depends(require_role("admin")),
                 db: Session = Depends(get_db)):
    """The alert list with the unread count for the bell (ADM-ACC-09)."""
    return AlertList(unread_count=alerts.unread_count(db),
                     items=[_alert_out(a) for a in alerts.list_alerts(db, unread_only)])


@admin.post("/alerts/read-all", status_code=204)
def admin_alerts_read_all(user: User = Depends(require_role("admin")),
                          db: Session = Depends(get_db)):
    alerts.mark_all_read(db)


@admin.post("/alerts/{alert_id}/read", status_code=204)
def admin_alert_read(alert_id: uuid.UUID, user: User = Depends(require_role("admin")),
                     db: Session = Depends(get_db)):
    alerts.mark_read(db, alert_id)
