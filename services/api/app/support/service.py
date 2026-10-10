"""Complaints, feedback, ratings and check-ins (ISS-, CMP-, FDBK-, SVC-07,
SVC-11, SVC-14, CHK-)."""
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.platform.clock import today_ist
from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.support import alerts, defaults
from app.support.models import (
    COMPLAINT_STATUSES,
    ISSUE_CATEGORIES,
    OPTION_KINDS,
    CheckIn,
    Complaint,
    ComplaintUpdate,
    Feedback,
    SupportOption,
    VisitRating,
)
from app.support.notify import EmailNotifier, PushNotifier
from app.support.schemas import (
    AdminComplaintDetail,
    AdminComplaintSummary,
    CheckInAdmin,
    CheckInAnswer,
    CheckInsReport,
    ComplaintDetail,
    ComplaintSummary,
    CrewRatings,
    FeedbackAdmin,
    OptionAdmin,
    OptionOut,
    Options,
    PendingCheckIn,
    RatingAdmin,
    RatingOut,
    RatingsReport,
    UpdateOut,
)

REPLY_WITHIN = timedelta(hours=4)  # ISS-06, ADM-CMP-06
CHECKIN_DAYS_BEFORE = 4  # CHK-01
CYCLE_DAYS = 30
CREW_RATINGS_DAYS = 30

_DEFAULTS = {
    "feedback_category": defaults.FEEDBACK_CATEGORIES,
    "positive_tag": defaults.POSITIVE_TAGS,
    "checkin_category": defaults.CHECKIN_CATEGORIES,
}


def display_id(number: int) -> str:
    return f"#C-{number:04d}"


def cycle_for(first_service: date, today: date) -> tuple[date, date] | None:
    """The 30-day billing cycle that contains `today`, as (start, renewal date).
    None before the first service date."""
    if today < first_service:
        return None
    whole_cycles = (today - first_service).days // CYCLE_DAYS
    start = first_service + timedelta(days=CYCLE_DAYS * whole_cycles)
    return start, start + timedelta(days=CYCLE_DAYS)


class SupportService:
    def __init__(self, db: Session, push: PushNotifier, email: EmailNotifier,
                 now: Callable[[], datetime] = utcnow,
                 today: Callable[[], date] = today_ist):
        self.db = db
        self.push = push
        self.email = email
        self._now = now
        self._today = today

    # People -----------------------------------------------------------

    def customer_for(self, login_id: uuid.UUID) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.login_id == login_id))
        if customer is None:
            raise ApiError("not_found", "No customer was found for this sign-in.", 404)
        return customer

    def _names(self, customer_ids: set[uuid.UUID]) -> dict[uuid.UUID, tuple[str, str, str]]:
        """Customer ID to (name, society, flat). Only admins ever see these."""
        if not customer_ids:
            return {}
        rows = self.db.execute(
            select(Customer.id, Customer.first_name, Customer.last_name, Society.name,
                   Customer.flat)
            .join(Society, Society.id == Customer.society_id)
            .where(Customer.id.in_(customer_ids)))
        return {r.id: (f"{r.first_name} {r.last_name}".strip(), r.name, r.flat) for r in rows}

    # Admin-editable lists ---------------------------------------------

    def _seed(self, kind: str) -> None:
        if self.db.scalar(select(func.count()).select_from(SupportOption)
                          .where(SupportOption.kind == kind)):
            return
        for order, (name, description) in enumerate(_DEFAULTS[kind]):
            self.db.add(SupportOption(kind=kind, name=name, description=description,
                                      sort_order=order))
        self.db.commit()

    def _active(self, kind: str) -> list[SupportOption]:
        self._seed(kind)
        return list(self.db.scalars(
            select(SupportOption)
            .where(SupportOption.kind == kind, SupportOption.active.is_(True))
            .order_by(SupportOption.sort_order, SupportOption.name)))

    def options(self) -> Options:
        def out(rows):
            return [OptionOut(id=o.id, name=o.name, description=o.description) for o in rows]
        return Options(
            issue_categories=list(ISSUE_CATEGORIES),
            feedback_categories=out(self._active("feedback_category")),
            positive_tags=out(self._active("positive_tag")),
            checkin_categories=out(self._active("checkin_category")))

    def all_options(self) -> list[OptionAdmin]:
        for kind in OPTION_KINDS:
            self._seed(kind)
        rows = self.db.scalars(
            select(SupportOption).order_by(SupportOption.kind, SupportOption.sort_order))
        return [OptionAdmin(id=o.id, kind=o.kind, name=o.name, description=o.description,
                            sort_order=o.sort_order, active=o.active) for o in rows]

    def add_option(self, kind: str, name: str, description: str) -> SupportOption:
        if kind not in OPTION_KINDS:
            raise ApiError("validation_failed", "Unknown list.", 422, {"kind": "Unknown list."})
        self._seed(kind)
        name = name.strip()
        if self.db.scalar(select(SupportOption).where(
                SupportOption.kind == kind, SupportOption.name == name)):
            raise ApiError("duplicate", "That name is already in the list.", 409)
        last = self.db.scalar(select(func.max(SupportOption.sort_order))
                              .where(SupportOption.kind == kind)) or 0
        option = SupportOption(kind=kind, name=name, description=description.strip(),
                               sort_order=last + 1)
        self.db.add(option)
        self.db.commit()
        return option

    def patch_option(self, option_id: uuid.UUID, name: str | None, description: str | None,
                     active: bool | None, sort_order: int | None) -> SupportOption:
        option = self.db.get(SupportOption, option_id)
        if option is None:
            raise ApiError("not_found", "That entry was not found.", 404)
        if name is not None:
            option.name = name.strip()
        if description is not None:
            option.description = description.strip()
        if active is not None:
            option.active = active
        if sort_order is not None:
            option.sort_order = sort_order
        self.db.commit()
        return option

    # Complaints -------------------------------------------------------

    def _updates(self, complaint_id: uuid.UUID) -> list[ComplaintUpdate]:
        return list(self.db.scalars(
            select(ComplaintUpdate).where(ComplaintUpdate.complaint_id == complaint_id)
            .order_by(ComplaintUpdate.created_at, ComplaintUpdate.id)))

    def _latest_notes(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """The newest admin note of each complaint (CMP-01)."""
        if not ids:
            return {}
        rows = self.db.scalars(
            select(ComplaintUpdate)
            .where(ComplaintUpdate.complaint_id.in_(ids), ComplaintUpdate.author_role == "admin",
                   ComplaintUpdate.note != "")
            .order_by(ComplaintUpdate.created_at))
        return {u.complaint_id: u.note for u in rows}

    def _summary(self, c: Complaint, note: str | None) -> dict:
        return dict(id=c.id, number=c.number, display_id=display_id(c.number),
                    category=c.category, description=c.description, status=c.status,
                    visit_id=c.visit_id, created_at=c.created_at, updated_at=c.updated_at,
                    latest_note=note)

    def _update_out(self, u: ComplaintUpdate) -> UpdateOut:
        return UpdateOut(id=u.id, author_role=u.author_role, note=u.note, status=u.status,
                         created_at=u.created_at)

    def create_complaint(self, customer: Customer, category: str, description: str,
                         visit_id: str | None, photo_keys: list[str]) -> ComplaintDetail:
        if category not in ISSUE_CATEGORIES:  # ISS-05
            raise ApiError("validation_failed", "Choose what went wrong.", 422,
                           {"category": "Choose what went wrong."})
        if not description.strip():
            raise ApiError("validation_failed", "Describe what happened.", 422,
                           {"description": "Describe what happened."})
        number = (self.db.scalar(select(func.max(Complaint.number))) or 0) + 1
        now = self._now()
        complaint = Complaint(number=number, customer_id=customer.id, category=category,
                              description=description.strip(), visit_id=visit_id or None,
                              photo_keys=photo_keys, created_at=now, updated_at=now)
        self.db.add(complaint)
        self.db.commit()
        # ADM-CMP-08
        alerts.raise_alert(
            self.db, "complaint_raised", f"New complaint {display_id(number)}",
            f"{customer.first_name}: {category}", ref_type="complaint", ref_id=str(complaint.id),
            push=self.push, email=self.email)
        return self.detail_for_customer(customer, complaint.id)

    def list_for_customer(self, customer: Customer) -> list[ComplaintSummary]:
        rows = list(self.db.scalars(
            select(Complaint).where(Complaint.customer_id == customer.id)
            .order_by(Complaint.created_at.desc(), Complaint.number.desc())))
        notes = self._latest_notes([c.id for c in rows])
        return [ComplaintSummary(**self._summary(c, notes.get(c.id))) for c in rows]

    def in_progress_count(self, customer: Customer) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Complaint)
            .where(Complaint.customer_id == customer.id, Complaint.status != "Resolved")) or 0

    def _own(self, customer: Customer, complaint_id: uuid.UUID) -> Complaint:
        c = self.db.get(Complaint, complaint_id)
        if c is None or c.customer_id != customer.id:
            raise ApiError("not_found", "That complaint was not found.", 404)
        return c

    def detail_for_customer(self, customer: Customer, complaint_id: uuid.UUID) -> ComplaintDetail:
        c = self._own(customer, complaint_id)
        updates = self._updates(c.id)
        notes = self._latest_notes([c.id])
        return ComplaintDetail(**self._summary(c, notes.get(c.id)), photo_keys=c.photo_keys or [],
                               updates=[self._update_out(u) for u in updates])

    def customer_message(self, customer: Customer, complaint_id: uuid.UUID,
                         note: str) -> ComplaintDetail:
        c = self._own(customer, complaint_id)
        if c.status == "Resolved":
            raise ApiError("complaint_resolved",
                           "This complaint is resolved. Please raise a new one.", 409)
        now = self._now()
        self.db.add(ComplaintUpdate(complaint_id=c.id, author_role="customer", note=note.strip(),
                                    created_at=now))
        c.updated_at = now
        self.db.commit()
        alerts.raise_alert(
            self.db, "complaint_reply", f"Reply on complaint {display_id(c.number)}",
            f"{customer.first_name}: {note.strip()[:200]}", ref_type="complaint",
            ref_id=str(c.id), push=self.push, email=self.email)
        return self.detail_for_customer(customer, c.id)

    # Admin side of complaints

    def _admin_summary(self, c: Complaint, note: str | None, names) -> dict:
        name, society, flat = names.get(c.customer_id, ("", "", ""))
        overdue = c.status == "Raised" and self._now() - c.created_at > REPLY_WITHIN
        return dict(self._summary(c, note), customer_name=name, society=society, flat=flat,
                    overdue=overdue)

    def list_for_admin(self, status: str | None,
                       category: str | None) -> list[AdminComplaintSummary]:
        query = select(Complaint).order_by(Complaint.created_at.desc(), Complaint.number.desc())
        if status:
            query = query.where(Complaint.status == status)
        if category:
            query = query.where(Complaint.category == category)
        rows = list(self.db.scalars(query))
        notes = self._latest_notes([c.id for c in rows])
        names = self._names({c.customer_id for c in rows})
        return [AdminComplaintSummary(**self._admin_summary(c, notes.get(c.id), names))
                for c in rows]

    def detail_for_admin(self, complaint_id: uuid.UUID) -> AdminComplaintDetail:
        c = self.db.get(Complaint, complaint_id)
        if c is None:
            raise ApiError("not_found", "That complaint was not found.", 404)
        notes = self._latest_notes([c.id])
        names = self._names({c.customer_id})
        return AdminComplaintDetail(
            **self._admin_summary(c, notes.get(c.id), names), photo_keys=c.photo_keys or [],
            updates=[self._update_out(u) for u in self._updates(c.id)])

    def _push_customer(self, c: Complaint, body: str) -> None:
        customer = self.db.get(Customer, c.customer_id)
        if customer is not None:
            # CMP-04: the "Complaint update" push.
            self.push.push_customer(customer.login_id, "Complaint update",
                                    f"{display_id(c.number)}: {body}")

    def admin_update(self, admin_id: uuid.UUID, complaint_id: uuid.UUID, status: str | None,
                     note: str) -> AdminComplaintDetail:
        c = self.db.get(Complaint, complaint_id)
        if c is None:
            raise ApiError("not_found", "That complaint was not found.", 404)
        if status is not None and status not in COMPLAINT_STATUSES:
            raise ApiError("validation_failed", "Unknown status.", 422,
                           {"status": "Unknown status."})
        note = note.strip()
        changed = status is not None and status != c.status
        if not changed and not note:
            return self.detail_for_admin(c.id)
        now = self._now()
        # One entry for each change, so the thread says who did what (ADM-CMP-07).
        if changed:
            c.status = status
            self.db.add(ComplaintUpdate(complaint_id=c.id, author_role="admin",
                                        author_login_id=admin_id, note=note, status=status,
                                        created_at=now))
        else:
            self.db.add(ComplaintUpdate(complaint_id=c.id, author_role="admin",
                                        author_login_id=admin_id, note=note, created_at=now))
        c.updated_at = now
        self.db.commit()
        text = note or f"Status is now {c.status}."
        self._push_customer(c, text)
        return self.detail_for_admin(c.id)

    def alert_overdue_complaints(self) -> int:
        """Alerts once for each complaint still Raised after 4 hours
        (ADM-CMP-08). Run by the scheduler every few minutes."""
        cutoff = self._now() - REPLY_WITHIN
        rows = list(self.db.scalars(
            select(Complaint).where(Complaint.status == "Raised",
                                    Complaint.created_at <= cutoff,
                                    Complaint.overdue_alerted_at.is_(None))))
        for c in rows:
            c.overdue_alerted_at = self._now()
            self.db.commit()
            alerts.raise_alert(
                self.db, "complaint_overdue", f"Complaint {display_id(c.number)} is waiting",
                "Still Raised after 4 hours.", ref_type="complaint", ref_id=str(c.id),
                push=self.push, email=self.email)
        return len(rows)

    # Feedback and ratings --------------------------------------------

    def give_feedback(self, customer: Customer, category: str | None, rating: int | None,
                      comment: str, permission: bool) -> Feedback:
        comment = comment.strip()
        if rating is None and not comment:  # FDBK-07
            raise ApiError("validation_failed", "Add a star rating or a comment.", 422,
                           {"rating": "Add a star rating or a comment."})
        if category:
            names = {o.name for o in self._active("feedback_category")}
            if category not in names:
                raise ApiError("validation_failed", "Choose a category from the list.", 422,
                               {"category": "Choose a category from the list."})
        row = Feedback(customer_id=customer.id, category=category or None, rating=rating,
                       comment=comment, testimonial_permission=permission, created_at=self._now())
        self.db.add(row)
        self.db.commit()
        return row

    def rate_visit(self, customer: Customer, visit_id: str, rating: int, tags: list[str],
                   comment: str, permission: bool) -> RatingOut:
        tags = list(dict.fromkeys(t.strip() for t in tags if t.strip()))
        # SVC-11: positive tags at 5 stars. SVC-14: issue tags below.
        allowed = {o.name for o in self._active(
            "positive_tag" if rating == 5 else "feedback_category")}
        if not set(tags) <= allowed:
            raise ApiError("validation_failed", "One of the tags is not in the list.", 422,
                           {"tags": "One of the tags is not in the list."})
        row = self.db.scalar(select(VisitRating).where(
            VisitRating.customer_id == customer.id, VisitRating.visit_id == visit_id))
        if row is None:
            row = VisitRating(customer_id=customer.id, visit_id=visit_id, created_at=self._now())
            self.db.add(row)
        row.rating = rating
        row.tags = tags
        row.comment = comment.strip()
        row.testimonial_permission = permission
        self.db.commit()
        return RatingOut(visit_id=row.visit_id, rating=row.rating, tags=row.tags,
                         comment=row.comment, testimonial_permission=row.testimonial_permission,
                         created_at=row.created_at)

    def crew_ratings(self) -> CrewRatings:
        since = self._now() - timedelta(days=CREW_RATINGS_DAYS)
        values = list(self.db.scalars(
            select(VisitRating.rating).where(VisitRating.created_at >= since)))
        stars = {str(n): values.count(n) for n in range(1, 6)}
        average = round(sum(values) / len(values), 1) if values else None
        return CrewRatings(period_days=CREW_RATINGS_DAYS, count=len(values), average=average,
                           stars=stars)

    def feedback_for_admin(self, category: str | None, rating: int | None) -> list[FeedbackAdmin]:
        query = select(Feedback).order_by(Feedback.created_at.desc())
        if category:
            query = query.where(Feedback.category == category)
        if rating:
            query = query.where(Feedback.rating == rating)
        rows = list(self.db.scalars(query))
        names = self._names({r.customer_id for r in rows})
        return [FeedbackAdmin(
            id=r.id, category=r.category, rating=r.rating, comment=r.comment,
            testimonial_permission=r.testimonial_permission,
            customer_name=names.get(r.customer_id, ("", "", ""))[0],
            society=names.get(r.customer_id, ("", "", ""))[1], created_at=r.created_at)
            for r in rows]

    def ratings_for_admin(self) -> RatingsReport:
        rows = list(self.db.scalars(select(VisitRating).order_by(VisitRating.created_at.desc())))
        names = self._names({r.customer_id for r in rows})
        tag_counts: dict[str, int] = {}
        for r in rows:
            for tag in r.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        average = round(sum(r.rating for r in rows) / len(rows), 2) if rows else None
        items = [RatingAdmin(
            visit_id=r.visit_id, rating=r.rating, tags=r.tags or [], comment=r.comment,
            testimonial_permission=r.testimonial_permission, created_at=r.created_at,
            society=names.get(r.customer_id, ("", "", ""))[1]) for r in rows]
        return RatingsReport(count=len(rows), average=average, tag_counts=tag_counts, items=items)

    # Monthly check-in -------------------------------------------------

    def _vehicle_label(self, vehicle: Vehicle) -> str:
        return " ".join(p for p in (vehicle.model, vehicle.registration) if p)

    def pending_checkins(self, customer: Customer) -> list[PendingCheckIn]:
        """The check-ins due now: in the last 4 days of a cycle and not yet
        given for it (CHK-01, CHK-08)."""
        today = self._today()
        rows = self.db.execute(
            select(Subscription, Vehicle)
            .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
            .where(Vehicle.customer_id == customer.id, Subscription.status == "Active"))
        pending = []
        for sub, vehicle in rows:
            cycle = cycle_for(sub.first_service_date, today)
            if cycle is None:
                continue
            start, renewal = cycle
            if today < renewal - timedelta(days=CHECKIN_DAYS_BEFORE):
                continue
            if self.db.scalar(select(CheckIn.id).where(
                    CheckIn.subscription_id == sub.id, CheckIn.cycle_start == start)):
                continue
            pending.append(PendingCheckIn(
                subscription_id=sub.id, vehicle_id=vehicle.id,
                vehicle_label=self._vehicle_label(vehicle), cycle_start=start,
                renewal_date=renewal))
        return pending

    def submit_checkin(self, customer: Customer, subscription_id: uuid.UUID,
                       answers: list[CheckInAnswer], comment: str) -> CheckIn:
        due = next((p for p in self.pending_checkins(customer)
                    if p.subscription_id == subscription_id), None)
        if due is None:
            raise ApiError("checkin_not_due",
                           "There is no check-in to give for this car right now.", 409)
        names = {o.name for o in self._active("checkin_category")}
        if any(a.category not in names for a in answers):
            raise ApiError("validation_failed", "One of the categories is not in the list.", 422,
                           {"answers": "One of the categories is not in the list."})
        row = CheckIn(customer_id=customer.id, subscription_id=subscription_id,
                      cycle_start=due.cycle_start,
                      answers=[{"category": a.category, "rating": a.rating} for a in answers],
                      comment=comment.strip(), created_at=self._now())
        self.db.add(row)
        self.db.commit()
        return row

    def notify_due_checkins(self) -> int:
        """Sends the check-in push (CHK-01) to each customer whose renewal is
        four days away today. Run once a day by the scheduler. Matching the
        exact day is what stops it being sent twice."""
        target = self._today() + timedelta(days=CHECKIN_DAYS_BEFORE)
        rows = self.db.execute(
            select(Subscription, Customer)
            .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
            .join(Customer, Customer.id == Vehicle.customer_id)
            .where(Subscription.status == "Active"))
        sent = 0
        for sub, customer in rows:
            cycle = cycle_for(sub.first_service_date, self._today())
            if cycle is None or cycle[1] != target:
                continue
            self.push.push_customer(customer.login_id, "Monthly check-in",
                                    "How is Priveo doing? Take a minute to tell us.")
            sent += 1
        return sent

    def checkins_for_admin(self) -> CheckInsReport:
        rows = list(self.db.execute(
            select(CheckIn, Vehicle)
            .join(Subscription, Subscription.id == CheckIn.subscription_id)
            .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
            .order_by(CheckIn.created_at.desc())))
        names = self._names({c.customer_id for c, _ in rows})
        totals: dict[str, list[int]] = {}
        items = []
        for c, vehicle in rows:
            for a in c.answers or []:
                totals.setdefault(a["category"], []).append(a["rating"])
            name, society, _ = names.get(c.customer_id, ("", "", ""))
            items.append(CheckInAdmin(
                id=c.id, customer_name=name, society=society,
                vehicle_label=self._vehicle_label(vehicle), cycle_start=c.cycle_start,
                answers=[CheckInAnswer(**a) for a in c.answers or []], comment=c.comment,
                created_at=c.created_at))
        averages = {k: round(sum(v) / len(v), 2) for k, v in totals.items()}
        return CheckInsReport(category_averages=averages, items=items)
