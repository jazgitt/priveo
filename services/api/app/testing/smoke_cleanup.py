"""Test environment only: removes the customer and crew the deployment smoke test creates.

`DELETE /v1/admin/test-users/{login_id}` answers 404 everywhere except
ENVIRONMENT=test. It accepts only a sign-in ID in the smoke-test number range
(SMOKE_LOGIN_ID), and only for a customer or crew login. It removes the login and
every row that refers to it, found through the foreign keys, children first.
Nothing outside that tree is touched.
"""
import re
import uuid
from functools import lru_cache

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Table, delete, select
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.identity.service import User
from app.platform.config import get_settings
from app.platform.db import Base, get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError

router = APIRouter(prefix="/v1/admin/test-users", tags=["test"], include_in_schema=False)

# The smoke test makes its customer and crew with numbers in 9000099000..9000099999.
SMOKE_LOGIN_ID = re.compile(r"9000099\d{3}")
MAX_DEPTH = 40


@lru_cache
def _references_into() -> dict[str, list[tuple[Table, str, str]]]:
    """For each table, the (child table, child column, parent column) of every foreign key into it."""
    refs: dict[str, list[tuple[Table, str, str]]] = {}
    for child in Base.metadata.tables.values():
        for fk in child.foreign_keys:
            refs.setdefault(fk.column.table.name, []).append(
                (child, fk.parent.name, fk.column.name))
    return refs


def _delete_rows(db: Session, table: Table, column: str, values: list, depth: int = 0) -> None:
    """Deletes the rows of `table` whose `column` is one of `values`, after the rows that refer to them."""
    if not values:
        return
    if depth > MAX_DEPTH:
        raise RuntimeError("The smoke-test cleanup reached too many levels of references.")
    children = _references_into().get(table.name, [])
    parent_columns = sorted({parent for _, _, parent in children})
    if parent_columns:
        rows = db.execute(select(*[table.c[name] for name in parent_columns])
                          .where(table.c[column].in_(values))).mappings().all()
        for child, child_column, parent_column in children:
            ids = sorted({row[parent_column] for row in rows if row[parent_column] is not None},
                         key=str)
            _delete_rows(db, child, child_column, ids, depth + 1)
    db.execute(delete(table).where(table.c[column].in_(values)))


@router.delete("/{login_id}", status_code=204)
def remove_smoke_user(login_id: str, _: User = Depends(require_role("admin")),
                      db: Session = Depends(get_db)) -> Response:
    if get_settings().environment != "test":
        raise ApiError("not_found", "Not found.", 404)
    if not SMOKE_LOGIN_ID.fullmatch(login_id):
        raise ApiError("validation_failed", "Only a smoke-test login can be removed.", 422)
    logins = db.scalars(select(Login).where(Login.login_id == login_id)).all()
    for login in logins:
        if login.role not in ("customer", "crew"):
            raise ApiError("validation_failed", "Only a smoke-test customer or crew can be removed.", 422)
    for login in logins:
        _delete_rows(db, Login.__table__, "id", [uuid.UUID(str(login.id))])
    db.commit()
    return Response(status_code=204)
