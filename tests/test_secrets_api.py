from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base, engine
from app.main import app, vault_state
from app.models import Secret

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


def test_admin_token_required() -> None:
    reset_state()
    client = TestClient(app)

    response = client.post("/unseal", json={"parts": ["key1", "key2", "key3"]})

    assert response.status_code == 401
