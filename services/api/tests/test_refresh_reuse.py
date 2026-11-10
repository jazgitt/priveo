"""Security review R-07: a refresh token that was already swapped for a new one
is a copied token if it comes back after the grace time. The session ends."""
from datetime import timedelta

from sqlalchemy import select

from app.identity.models import AuthEvent, AuthSession
from app.identity.service import REFRESH_REUSE_GRACE
from app.platform.db import utcnow
from tests.test_api import auth, login


def _refresh(client, token):
    return client.post("/v1/auth/refresh", json={"refresh_token": token})


def _session(db, role_token_session_count=1):
    db.expire_all()
    rows = list(db.scalars(select(AuthSession).order_by(AuthSession.created_at)))
    assert len(rows) >= role_token_session_count
    return rows[-1]


def _age_rotation(db, session, by):
    session.rotated_at = utcnow() - by
    db.commit()


def test_normal_refresh_chain_keeps_working(client, db):
    data = login(client, "crew")
    for _ in range(3):
        r = _refresh(client, data["refresh_token"])
        assert r.status_code == 200
        data = r.json()
    assert client.get("/v1/crew/visits", headers=auth(data["access_token"])).status_code == 200
    assert _session(db).ended_at is None


def test_old_token_inside_the_grace_time_is_refused_but_the_session_lives(client, db):
    first = login(client, "crew")
    second = _refresh(client, first["refresh_token"]).json()
    # The phone lost the reply and tries again with the token it still has.
    assert _refresh(client, first["refresh_token"]).status_code == 401
    session = _session(db)
    assert session.ended_at is None
    assert db.scalar(select(AuthEvent).where(AuthEvent.kind == "refresh_reuse")) is None
    # The newer token still works.
    assert _refresh(client, second["refresh_token"]).status_code == 200


def test_old_token_after_the_grace_time_ends_the_session(client, db):
    first = login(client, "customer")
    second = _refresh(client, first["refresh_token"]).json()
    _age_rotation(db, _session(db), REFRESH_REUSE_GRACE + timedelta(seconds=1))

    assert _refresh(client, first["refresh_token"]).status_code == 401

    session = _session(db)
    assert session.ended_at is not None and session.ended_reason == "token_reuse"
    assert db.scalar(select(AuthEvent).where(AuthEvent.kind == "refresh_reuse")) is not None
    # The newer token, the access token and the next refresh are all dead.
    assert _refresh(client, second["refresh_token"]).status_code == 401
    assert client.get("/v1/customer/home",
                      headers=auth(second["access_token"])).status_code == 401


def test_reuse_only_ends_the_session_it_belongs_to(client, db):
    phone = login(client, "crew")
    other = login(client, "customer")
    _refresh(client, phone["refresh_token"])
    stolen_session = db.scalar(select(AuthSession).where(
        AuthSession.previous_refresh_hash.is_not(None)))
    _age_rotation(db, stolen_session, REFRESH_REUSE_GRACE + timedelta(minutes=1))
    assert _refresh(client, phone["refresh_token"]).status_code == 401
    assert client.get("/v1/customer/home",
                      headers=auth(other["access_token"])).status_code == 200
    assert _refresh(client, other["refresh_token"]).status_code == 200


def test_an_invented_token_changes_nothing(client, db):
    login(client, "crew")
    assert _refresh(client, "not-a-real-token").status_code == 401
    assert _session(db).ended_at is None
    assert db.scalar(select(AuthEvent).where(AuthEvent.kind == "refresh_reuse")) is None


def test_reuse_of_an_already_ended_session_adds_no_second_event(client, db):
    first = login(client, "crew")
    _refresh(client, first["refresh_token"])
    _age_rotation(db, _session(db), REFRESH_REUSE_GRACE + timedelta(minutes=1))
    assert _refresh(client, first["refresh_token"]).status_code == 401
    assert _refresh(client, first["refresh_token"]).status_code == 401
    events = db.scalars(select(AuthEvent).where(AuthEvent.kind == "refresh_reuse")).all()
    assert len(events) == 1


def test_two_calls_with_the_same_token_have_one_winner(client, db, monkeypatch):
    """The swap is conditional on the token still being current: when another call
    swaps between this one's lookup and its update, this one is refused."""
    import pytest
    from sqlalchemy.orm import Session

    from app.identity.service import AuthService
    from app.platform.config import get_settings

    first = login(client, "crew")
    engine = db.get_bind()
    real_live = AuthService._live
    raced = []

    def live_then_lose_the_race(self, session):
        result = real_live(self, session)
        if not raced:
            raced.append(True)
            with Session(engine) as other:
                AuthService(get_settings(), other).refresh(first["refresh_token"])
        return result

    monkeypatch.setattr(AuthService, "_live", live_then_lose_the_race)
    with Session(engine) as loser, pytest.raises(Exception) as caught:
        AuthService(get_settings(), loser).refresh(first["refresh_token"])
    assert caught.value.status == 401
    # Exactly one swap happened: the session holds one previous token.
    assert _session(db).previous_refresh_hash is not None
