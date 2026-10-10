from fastapi import Depends
from sqlalchemy.orm import Session

from app.customer_reads.repository import InMemoryVisitReadRepository, VisitReadRepository
from app.customer_reads.service import CustomerReads
from app.platform.db import get_db

_default = InMemoryVisitReadRepository()


def get_visit_read_repository() -> VisitReadRepository:
    """An empty in-memory repository until the SQL one is bound at integration.
    Bind it with `app.dependency_overrides` or by replacing this function."""
    return _default


def get_customer_reads(db: Session = Depends(get_db),
                       visits: VisitReadRepository = Depends(get_visit_read_repository),
                       ) -> CustomerReads:
    return CustomerReads(db, visits)
