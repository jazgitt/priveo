from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401  (registers the tables)
from app.platform.config import get_settings
from app.platform.db import Base, make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    # A test can pass its own address with `-x url=...`.
    url = context.get_x_argument(as_dictionary=True).get("url") or get_settings().database_url
    if not url:
        raise SystemExit("DATABASE_URL is not set.")
    return url


def run_migrations_online() -> None:
    with make_engine(_url()).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not used.")
run_migrations_online()
