"""Seeds the logins. Run after the migrations: python scripts/seed.py

Reads DATABASE_URL, ADMIN_PASSWORD (or MOCK_ADMIN_PASSWORD) and, for dev,
SEED_DEMO_LOGINS with MOCK_CUSTOMER_PASSWORD and MOCK_CREW_PASSWORD.
Prints login IDs and what happened, never a password.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.directory.seed import seed_defaults
from app.identity.seed import seed_logins
from app.platform.config import get_settings
from app.platform.db import get_engine
from app.platform.sync_guard import restored_from_prod


def main() -> None:
    engine = get_engine()
    # A database copied from prod is never seeded: the deploy runs this script on
    # every release, and it must not change the copied data. Exit 0 so the deploy passes.
    when = restored_from_prod(engine)
    if when:
        print(f"seed skipped: this database was copied from prod at {when}.")
        return
    with Session(engine) as db:
        for login_id, outcome in seed_logins(db, get_settings()).items():
            print(f"{login_id}: {outcome}")
        # The sample plan, add-ons and vehicle catalogue are never put on prod.
        starter = get_settings().environment != "prod"
        print(f"directory defaults added: {seed_defaults(db, starter_data=starter)}")


if __name__ == "__main__":
    main()
