import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.models  # noqa: F401  (registers the tables)
from app.platform.db import Base, make_engine


def test_migrations_build_the_tables_the_models_describe(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'm.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")

    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "head")

    built = inspect(engine)
    for table in Base.metadata.sorted_tables:
        columns = {c["name"] for c in built.get_columns(table.name)}
        assert columns == {c.name for c in table.columns}, table.name

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
