import os
import subprocess
import sys

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


def test_the_running_app_knows_every_table():
    """The app is started on its own, as on the host, without the test
    set-up. A table it has not loaded breaks any save that links to it."""
    code = ("from app.main import app; import app.models as m; "
            "from app.platform.db import Base; "
            "from sqlalchemy.orm import configure_mappers; configure_mappers(); "
            "[fk.column for t in Base.metadata.tables.values() for fk in t.foreign_keys]; "
            "print(len(Base.metadata.tables))")
    only_app = code.replace("import app.models as m; ", "")
    counts = [subprocess.run([sys.executable, "-c", c], capture_output=True, text=True,
                             check=True).stdout.strip() for c in (only_app, code)]
    assert counts[0] == counts[1] != "0"
