from fastapi import Depends
from sqlalchemy.orm import Session

from app.customer_reads.repository import VisitReadRepository
from app.customer_reads.service import CustomerReads
from app.customer_reads.sql_repository import SqlVisitReadRepository
from app.media.store import ObjectStore, get_object_store
from app.platform.db import get_db


def get_visit_read_repository(db: Session = Depends(get_db),
                              store: ObjectStore = Depends(get_object_store),
                              ) -> VisitReadRepository:
    """Reads the scheduler's `visits` and `jobs` tables, with each job's proof
    as signed read URLs from the object store. Tests replace it with
    `app.dependency_overrides`."""
    return SqlVisitReadRepository(db, store)


def get_customer_reads(db: Session = Depends(get_db),
                       visits: VisitReadRepository = Depends(get_visit_read_repository),
                       store: ObjectStore = Depends(get_object_store),
                       ) -> CustomerReads:
    return CustomerReads(db, visits, store)
