"""Which society an audit row belongs to (ADM-AUD-01).

The audit trail of one site shows the changes made to that society's data: the
society itself, its zones and working slots, its customers, vehicles,
subscriptions, payments, crew, schedules and jobs. The society is found from
the row the entry points at. A change that belongs to no society (settings,
plans, the add-on catalogue, checklists, reasons, feature flags, admin logins,
batch actions) has none, and shows in no site's trail.
"""
import uuid

from sqlalchemy.orm import Session


def _uuid(value) -> uuid.UUID | None:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _find(session: Session, model, row_id):
    """A row by id, including one added in this flush and not yet written."""
    for obj in session.new:
        if isinstance(obj, model) and obj.id == row_id:
            return obj
    return session.get(model, row_id)


def society_of(session: Session, entity: str, entity_id, detail: dict | None = None) -> uuid.UUID | None:
    from app.addons.models import AddonBooking
    from app.billing.models import Payment
    from app.changes.models import ScheduleChange
    from app.crew.models import CrewMember
    from app.customers.models import AddonRequest, Customer, Subscription, Vehicle
    from app.directory.models import Society, WorkingSlot, WorkingSlotException, Zone
    from app.scheduling.models import Job, Schedule, SchedulingCrew, Visit

    def of_customer(customer_id) -> uuid.UUID | None:
        c = _find(session, Customer, customer_id) if customer_id else None
        return c.society_id if c else None

    def of_vehicle(vehicle_id) -> uuid.UUID | None:
        v = _find(session, Vehicle, vehicle_id) if vehicle_id else None
        return (v.society_id or of_customer(v.customer_id)) if v else None

    def of_visit(visit_id) -> uuid.UUID | None:
        visit = _find(session, Visit, visit_id)
        sched = _find(session, Schedule, visit.schedule_id) if visit else None
        return sched.society_id if sched else None

    key = _uuid(entity_id)
    if entity == "queue":  # "<crew id>:<day>"
        key = _uuid(str(entity_id).split(":")[0])
    if key is not None:
        found = None
        if entity == "society":
            found = key if _find(session, Society, key) else None
        elif entity == "zone":
            row = _find(session, Zone, key)
            found = row.society_id if row else None
        elif entity == "slot":
            row = _find(session, WorkingSlot, key)
            found = row.society_id if row else None
        elif entity == "slot_exception":
            row = _find(session, WorkingSlotException, key)
            found = row.society_id if row else None
        elif entity == "customer":
            found = of_customer(key)
        elif entity in ("vehicle", "parking"):
            found = of_vehicle(key)
        elif entity == "subscription":
            sub = _find(session, Subscription, key)
            found = of_vehicle(sub.vehicle_id) if sub else None
        elif entity == "payment":
            pay = _find(session, Payment, key)
            found = of_customer(pay.customer_id) if pay else None
        elif entity in ("schedule_change", "cutoff_request"):
            change = _find(session, ScheduleChange, key)
            found = of_customer(change.customer_id) if change else None
        elif entity == "addon":
            row = _find(session, AddonBooking, key) or _find(session, AddonRequest, key)
            found = of_customer(row.customer_id) if row else None
        elif entity == "schedule":
            row = _find(session, Schedule, key)
            found = row.society_id if row else None
        elif entity == "job":
            job = _find(session, Job, key)
            found = of_visit(job.visit_id) if job else None
        elif entity == "operations":  # a visit, or a job
            job = _find(session, Job, key)
            found = of_visit(job.visit_id) if job else of_visit(key)
        elif entity in ("crew", "queue"):
            row = _find(session, CrewMember, key) or _find(session, SchedulingCrew, key)
            found = row.society_id if row else None
        if found:
            return found
    # A create that names its society (a zone) is scoped by it.
    named = _uuid((detail or {}).get("society_id")) if isinstance(detail, dict) else None
    return named if named and _find(session, Society, named) else None
