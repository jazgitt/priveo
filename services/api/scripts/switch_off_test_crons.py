"""Switch every scheduled job off on the test database (owner decision, 9-Nov-26).

    DATABASE_URL=<test>  ENVIRONMENT=test  python scripts/switch_off_test_crons.py

Writes the `cron_jobs` switch to off for every registered job, including the
ones with no row (their default is on for two jobs, so a missing row is not
enough). A switched-off job answers `skipped` and does nothing, so the Vercel
cron calls still arrive every day but change no data. Refuses unless
ENVIRONMENT is `test`. Also run by `sync_prod_to_test.py` after each copy.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.main  # noqa: F401  (registers the jobs, including mani-retention)
from app.notifications.cron import JOBS
from app.notifications.models import CronJob
from app.platform.config import get_settings
from app.platform.db import get_engine, utcnow


def registered_jobs() -> list[str]:
    return sorted(JOBS)


def switch_off(db: Session) -> list[str]:
    """Returns the job names switched off. The caller commits."""
    names = registered_jobs()
    for name in names:
        row = db.get(CronJob, name)
        if row is None:
            db.add(CronJob(job=name, enabled=False, updated_at=utcnow()))
        else:
            row.enabled = False
            row.updated_at = utcnow()
    return names


def main() -> int:
    settings = get_settings()
    if settings.environment != "test":
        print(f"Refused: ENVIRONMENT is {settings.environment!r}, not 'test'.")
        return 2
    with Session(get_engine()) as db:
        names = switch_off(db)
        db.commit()
        for name in names:
            print(f"{name}: off")
    print(f"{len(names)} scheduled jobs are off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
