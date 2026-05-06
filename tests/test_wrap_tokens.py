from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crypto import hash_token
from app.db import Base, engine
from app.main import app, vault_state
from app.models import WrapToken, utc_now

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
