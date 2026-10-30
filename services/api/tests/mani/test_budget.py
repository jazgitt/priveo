"""The usage budget: one total, no period (D18)."""
import uuid
from decimal import Decimal

from app.mani import budget
from app.mani.config import ManiSettings
from app.mani.models import ManiModelUsage


def add(db, cost, run_id=None, kind="chat", ok=True):
    db.add(ManiModelUsage(run_id=run_id, kind=kind, backend="openrouter", model="m", cost_usd=Decimal(str(cost)),
                          ok=ok))
    db.flush()


def test_nothing_spent_is_zero(db):
    assert budget.spent_usd(db) == 0
    state = budget.check(db, ManiSettings(_env_file=None, budget_usd=1.0))
    assert (state.spent, state.budget, state.exhausted) == (0, Decimal("1.0"), False)


def test_spent_is_the_sum_of_all_rows_of_every_kind(db):
    add(db, "0.25")
    add(db, "0.10", kind="embedding")
    add(db, "0.05", ok=False)
    assert budget.spent_usd(db) == Decimal("0.40")


def test_exhausted_exactly_at_the_budget(db):
    cfg = ManiSettings(_env_file=None, budget_usd=0.5)
    add(db, "0.49999999")
    assert not budget.check(db, cfg).exhausted
    add(db, "0.00000001")
    assert budget.check(db, cfg).exhausted


def test_a_local_model_never_uses_the_budget(db):
    for _ in range(20):
        add(db, 0)
    assert not budget.check(db, ManiSettings(_env_file=None, budget_usd=0.01)).exhausted


def test_raising_the_budget_lifts_the_stop(db):
    add(db, 2)
    assert budget.check(db, ManiSettings(_env_file=None, budget_usd=1.0)).exhausted
    assert not budget.check(db, ManiSettings(_env_file=None, budget_usd=5.0)).exhausted


def test_the_per_request_limit_counts_only_that_run(db):
    from app.identity.models import Login
    from app.mani.models import ManiConversation, ManiRun
    login = Login(role="admin", login_id="priveopapa", display_name="F", password_hash="x")
    db.add(login)
    db.flush()
    conv = ManiConversation(login_id=login.id)
    db.add(conv)
    db.flush()
    one, two = ManiRun(conversation_id=conv.id), ManiRun(conversation_id=conv.id)
    db.add_all([one, two])
    db.flush()
    add(db, "0.7", run_id=one.id)
    add(db, "0.2", run_id=two.id)
    cfg = ManiSettings(_env_file=None, budget_usd=100, per_request_budget_usd=0.5)
    assert budget.request_limit_reached(db, cfg, one.id)
    assert not budget.request_limit_reached(db, cfg, two.id)
    assert not budget.request_limit_reached(db, cfg, uuid.uuid4())
    assert not budget.request_limit_reached(db, ManiSettings(_env_file=None, per_request_budget_usd=0), one.id)
