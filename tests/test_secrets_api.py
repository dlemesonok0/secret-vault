from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base, engine
from app.main import app, vault_state
from app.models import AuditEvent, Secret

ADMIN_HEADERS = {"Authorization": "Bearer change-me"}


def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    vault_state.seal()


def test_secret_crud_and_plaintext_not_stored() -> None:
    reset_state()
    client = TestClient(app)

    sealed_response = client.post(
        "/secrets",
        json={"name": "database_password", "value": "super-secret-password"},
        headers=ADMIN_HEADERS,
    )
    assert sealed_response.status_code == 423

    unseal_response = client.post(
        "/unseal",
        json={"parts": ["key1", "key2", "key3"]},
        headers=ADMIN_HEADERS,
    )
    assert unseal_response.status_code == 200

    create_response = client.post(
        "/secrets",
        json={"name": "database_password", "value": "super-secret-password"},
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 200

    get_response = client.get("/secrets/database_password", headers=ADMIN_HEADERS)
    assert get_response.status_code == 200
    assert get_response.json()["value"] == "super-secret-password"

    with Session(engine) as db:
        stored = db.query(Secret).filter(Secret.name == "database_password").one()
        assert "super-secret-password" not in stored.ciphertext
        assert stored.ciphertext != "super-secret-password"
        assert stored.crypto_version == 1

    update_response = client.post(
        "/secrets",
        json={"name": "database_password", "value": "new-password"},
        headers=ADMIN_HEADERS,
    )
    assert update_response.status_code == 200
    assert client.get("/secrets/database_password", headers=ADMIN_HEADERS).json()["value"] == "new-password"

    delete_response = client.delete("/secrets/database_password", headers=ADMIN_HEADERS)
    assert delete_response.status_code == 200
    assert client.get("/secrets/database_password", headers=ADMIN_HEADERS).status_code == 404

    with Session(engine) as db:
        event_types = {event.event_type for event in db.query(AuditEvent).all()}
        assert "secret.upsert" in event_types
        assert "secret.delete" in event_types


def test_admin_token_required() -> None:
    reset_state()
    client = TestClient(app)

    response = client.post("/unseal", json={"parts": ["key1", "key2", "key3"]})

    assert response.status_code == 401


def test_ready_and_ui_endpoints() -> None:
    reset_state()
    client = TestClient(app)

    assert client.get("/ready").json() == {"status": "ok"}
    assert "Secret Vault Admin" in client.get("/ui").text
    assert "Unwrap Secret" in client.get("/unwrap-ui").text
