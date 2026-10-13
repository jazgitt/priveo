"""Issued job definitions, independent of mutable directory labels/order."""
from sqlalchemy import select

from app.directory import lookup
from app.visits.models import JobChecklistProgress


def items_for_job(db, job):
    if job.checklist_snapshot is not None:
        return [lookup.ChecklistEntry(i["key"], i["label"])
                for i in job.checklist_snapshot["items"]]
    # Compatibility for legacy/unmigrated fixtures. Original labels are unknown.
    items = list(lookup.checklist_for(db, job.service))
    shown = {i.key for i in items}
    for key in db.scalars(select(JobChecklistProgress.item_key).where(
        JobChecklistProgress.job_id == job.id
    )):
        if key not in shown:
            items.append(lookup.ChecklistEntry(
                key, lookup.checklist_label(db, job.service, key) or key))
    return items
