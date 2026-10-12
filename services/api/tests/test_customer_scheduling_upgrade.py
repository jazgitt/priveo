"""Verify the upgrade preserves existing identities, vehicle ownership and proof."""

import os
import uuid
from datetime import UTC, date, datetime, time

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.platform.db import Base, make_engine


def test_existing_societies_and_addon_proof_survive_upgrade(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = Config("alembic.ini")
    config.cmd_opts = type("Options", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "0021")
    metadata = sa.MetaData()
    metadata.reflect(bind=engine)
    values = {}
    with engine.begin() as conn:

        def put(table_name, **extra):
            table = metadata.tables[table_name]
            row = {}
            for c in table.columns:
                if c.name in extra:
                    row[c.name] = extra[c.name]
                elif c.nullable:
                    row[c.name] = None
                elif isinstance(c.type, sa.Boolean):
                    row[c.name] = False
                elif isinstance(c.type, sa.Integer):
                    row[c.name] = 0
                elif isinstance(c.type, sa.JSON):
                    row[c.name] = []
                elif isinstance(c.type, sa.DateTime):
                    row[c.name] = datetime.now(UTC)
                elif isinstance(c.type, sa.Date):
                    row[c.name] = date(2026, 10, 18)
                elif isinstance(c.type, sa.Time):
                    row[c.name] = time(9)
                elif c.name == "id":
                    new = uuid.uuid4()
                    row[c.name] = new.hex if engine.dialect.name == "sqlite" else new
                else:
                    row[c.name] = ""
            conn.execute(table.insert().values(**row))
            values[table_name] = row
            return row["id"]

        society = put("societies", name="Legacy society", active=True)
        login = put("logins", role="customer", login_id="legacy@example.com", active=True)
        customer = put("customers", login_id=login, society_id=society, email="legacy@example.com")
        vehicle = put("vehicles", customer_id=customer, registration="HR01ZZ1234", model="Nexon")
        schedule = put("schedules", society_id=society, status="Frozen")
        visit = put("visits", schedule_id=schedule, vehicle_id=vehicle, status="Scheduled")
        addon = put("addon_requests", customer_id=customer, vehicle_id=vehicle, service="Deep Spa")
        put(
            "jobs",
            visit_id=visit,
            service="Cleaning-External",
            duration_minutes=20,
            status="Completed",
        )
        spa = put(
            "jobs",
            visit_id=visit,
            service="Deep Spa",
            duration_minutes=120,
            status="Scheduled",
            addon_request_id=addon,
        )
        proof = put(
            "media_uploads",
            owner_login_id=login,
            job_id=spa,
            purpose="proof",
            kind="photo",
            stage="After",
            status="Confirmed",
            object_key="proof/legacy.jpg",
        )
    command.upgrade(config, "head")
    metadata.clear()
    metadata.reflect(bind=engine)
    with engine.connect() as conn:
        vehicles, jobs, visits = (metadata.tables[t] for t in ("vehicles", "jobs", "visits"))
        assert (
            conn.scalar(sa.select(vehicles.c.society_id).where(vehicles.c.id == vehicle)) == society
        )
        new_visit = conn.scalar(sa.select(jobs.c.visit_id).where(jobs.c.id == spa))
        assert new_visit != visit
        assert conn.scalar(
            sa.select(visits.c.addon_key).where(visits.c.id == new_visit)
        ).startswith("legacy:")
        media = metadata.tables["media_uploads"]
        assert conn.scalar(sa.select(media.c.job_id).where(media.c.id == proof)) == spa
        assert conn.scalar(sa.select(visits.c.status).where(visits.c.id == visit)) == "Completed"
    engine.dispose()
