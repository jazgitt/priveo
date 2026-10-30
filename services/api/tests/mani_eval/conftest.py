"""One dataset for the whole eval test module: building it takes a few seconds."""
import pytest
from sqlalchemy.orm import Session

from tests.mani_eval.dataset import FIXED_NOW, build_dataset, make_engine_at
from tests.mani_eval.expected import compute_all


@pytest.fixture(scope="session")
def eval_world(tmp_path_factory):
    engine = make_engine_at(tmp_path_factory.mktemp("mani-eval") / "eval.sqlite3")
    with Session(engine) as db:
        dataset = build_dataset(db, FIXED_NOW)
        expected = compute_all(db, FIXED_NOW)
        yield {"engine": engine, "db": db, "dataset": dataset, "expected": expected}
    engine.dispose()
