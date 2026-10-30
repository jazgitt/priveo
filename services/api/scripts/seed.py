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


def main() -> None:
    with Session(get_engine()) as db:
        for login_id, outcome in seed_logins(db, get_settings()).items():
            print(f"{login_id}: {outcome}")
        # The sample plan, add-ons and vehicle catalogue are never put on prod.
        starter = get_settings().environment != "prod"
        print(f"directory defaults added: {seed_defaults(db, starter_data=starter)}")


if __name__ == "__main__":
    main()
