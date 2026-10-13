"""Add synthetic scenarios to the hosted dev DB without resetting existing data."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.directory.models import Plan, Society
from app.identity.models import Login
from app.identity.service import hash_password
from app.platform.clock import today_ist
from app.platform.config import get_settings
from app.platform.db import get_engine
from scripts.test_data import _seed_scenario, catalogue, identity


def seed_additive(engine, day, password):
    if not password:
        raise ValueError("TEST_DATA_PASSWORD is required.")
    snapshots = []
    added = []
    with Session(engine) as db, db.begin():
        if engine.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(798975)"))
        admins = list(db.scalars(select(Login).where(Login.role == "admin")))
        if len(admins) != 1 or admins[0].login_id != "priveopapa":
            raise ValueError("Expected the existing single priveopapa Admin.")
        db.execute(text("CREATE TABLE IF NOT EXISTS shared_test_data_manifest "
                        "(scenario TEXT PRIMARY KEY, snapshot TEXT NOT NULL)"))
        shared = [
            Society(id=identity("shared", "secondary-society"),
                    name="TEST Secondary Society", city="Synthetic City",
                    sector="Cross-society fixtures"),
            Plan(id=identity("shared", "internal-plan"), name="TEST External + Internal",
                 monthly_price_rupees=999, includes_interior=True,
                 inclusions=["Daily external cleaning", "Weekly internal cleaning"]),
            Plan(id=identity("shared", "external-plan"), name="TEST External Only",
                 monthly_price_rupees=699, includes_interior=False,
                 inclusions=["Daily external cleaning"]),
        ]
        for row in shared:
            existing = db.get(type(row), row.id)
            if existing is None:
                db.add(row)
            elif existing.name != row.name:
                raise ValueError("Shared synthetic fixture ID collision.")
        db.flush()
        password_hash = hash_password(password)
        for config in catalogue():
            scenario = config["id"]
            saved = db.scalar(text("SELECT snapshot FROM shared_test_data_manifest "
                                   "WHERE scenario=:scenario"), {"scenario": scenario})
            login = db.get(Login, identity(scenario, "customer-login"))
            if saved:
                if login is None or login.login_id != f"test.{scenario.lower()}@priveo.test":
                    raise ValueError(f"Stored scenario {scenario} has missing/conflicting data.")
                snapshots.append(json.loads(saved))
                continue  # Preserve manual changes and existing scenario passwords.
            if login or db.get(Society, identity(scenario, "society")):
                raise ValueError(f"Untracked scenario collision: {scenario}.")
            snapshot = _seed_scenario(db, config, day, password_hash)
            db.execute(text("INSERT INTO shared_test_data_manifest(scenario,snapshot) "
                            "VALUES (:scenario,:snapshot)"),
                       {"scenario": scenario, "snapshot": json.dumps(snapshot)})
            snapshots.append(snapshot)
            added.append(scenario)
    return {"version": 1, "admin_login": "priveopapa", "scenarios": snapshots,
            "added": added, "limitations": [
                "Additive seed only: existing scenarios and Admin credentials are preserved.",
                "Historical jobs have no proof media; upload it through the application.",
                "Normal hosted billing and cron jobs may evolve the scenario data.",
                "Offline queues and native provider delivery require device tests."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = get_settings()
    if settings.environment != "dev":
        parser.error("Hosted synthetic seeding is allowed only for ENVIRONMENT=dev.")
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        parser.error("Use the local fixture tool for SQLite; hosted seeding needs PostgreSQL.")
    with engine.connect() as connection:
        if connection.scalar(text("SELECT version_num FROM alembic_version")) != "0028":
            parser.error("Expected the reviewed application schema revision 0028.")
    if not args.apply:
        print("Preview: add missing synthetic scenarios; preserve existing data:")
        print(", ".join(item["id"] for item in catalogue()))
        return
    result = seed_additive(engine, today_ist(), os.environ.get("TEST_DATA_PASSWORD", ""))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Added {len(result['added'])} scenarios; manifest contains {len(result['scenarios'])}.")


if __name__ == "__main__":
    main()
