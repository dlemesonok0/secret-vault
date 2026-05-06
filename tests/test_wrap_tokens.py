from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crypto import hash_token
from app.db import Base, engine
from app.main import app, vault_state
from app.models import AuditEvent, WrapToken, utc_now
from app.rate_limit import InMemoryRateLimiter

ADMIN_HEADERS = {"Authorization": "Bearer change-me"}


def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    vault_state.seal()


def unseal_and_create_secret(client: TestClient) -> None:
    client.post("/unseal", json={"parts": ["key1", "key2", "key3"]}, headers=ADMIN_HEADERS)
    client.post(
        "/secrets",
        json={"name": "database_password", "value": "super-secret-password"},
        headers=ADMIN_HEADERS,
    )


def test_wrap_token_unwrap_is_one_time_and_hashed() -> None:
    reset_state()
    client = TestClient(app)
    unseal_and_create_secret(client)

    wrap_response = client.post(
        "/secrets/database_password/wrap",
        json={"ttl_seconds": 60},
        headers=ADMIN_HEADERS,
    )
    assert wrap_response.status_code == 200
    token = wrap_response.json()["token"]

    with Session(engine) as db:
        stored = db.query(WrapToken).one()
        assert stored.token_hash == hash_token(token)
        assert stored.token_hash != token

    unwrap_response = client.post("/unwrap", json={"token": token})
    assert unwrap_response.status_code == 200
    assert unwrap_response.json() == {
        "name": "database_password",
        "value": "super-secret-password",
    }

    repeated_response = client.post("/unwrap", json={"token": token})
    assert repeated_response.status_code == 409

    with Session(engine) as db:
        outcomes = {event.outcome for event in db.query(AuditEvent).filter(AuditEvent.event_type == "unwrap").all()}
        assert "success" in outcomes
        assert "already_used" in outcomes


def test_expired_wrap_token_does_not_work() -> None:
    reset_state()
    client = TestClient(app)
    unseal_and_create_secret(client)

    wrap_response = client.post(
        "/secrets/database_password/wrap",
        json={"ttl_seconds": 60},
        headers=ADMIN_HEADERS,
    )
    token = wrap_response.json()["token"]

    with Session(engine) as db:
        stored = db.query(WrapToken).one()
        stored.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    response = client.post("/unwrap", json={"token": token})

    assert response.status_code == 410


def test_rate_limiter_blocks_after_limit() -> None:
    class Client:
        host = "127.0.0.1"

    class Request:
        client = Client()

    limiter = InMemoryRateLimiter()
    limiter.check(Request(), limit=1, window_seconds=60)

    with pytest.raises(HTTPException) as exc:
        limiter.check(Request(), limit=1, window_seconds=60)

    assert exc.value.status_code == 429
