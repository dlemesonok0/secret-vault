from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.config import Settings, get_settings
from app.crypto import decrypt_secret, encrypt_secret, hash_token
from app.db import get_db, init_db
from app.errors import conflict, gone, not_found
from app.models import Secret, WrapToken, utc_now
from app.schemas import (
    HealthResponse,
    MessageResponse,
    SecretResponse,
    SecretUpsertRequest,
    StatusResponse,
    UnsealRequest,
    UnwrapRequest,
    WrapRequest,
    WrapResponse,
)
from app.tokens import create_wrap_token, normalize_utc
from app.vault import VaultState

settings = get_settings()
vault_state = VaultState(min_parts=settings.unseal_min_parts)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    vault_state.seal()
    yield


app = FastAPI(title="Secret Vault", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    return StatusResponse(sealed=vault_state.is_sealed())


@app.post("/unseal", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def unseal(payload: UnsealRequest) -> MessageResponse:
    vault_state.unseal(payload.parts)
    return MessageResponse(sealed=False, message="Vault unsealed")


@app.post("/seal", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def seal() -> MessageResponse:
    vault_state.seal()
    return MessageResponse(sealed=True, message="Vault sealed")


@app.post("/secrets", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def upsert_secret(payload: SecretUpsertRequest, db: Session = Depends(get_db)) -> MessageResponse:
    master_key = vault_state.require_unsealed()
    nonce, ciphertext = encrypt_secret(master_key, payload.value)
    secret = db.query(Secret).filter(Secret.name == payload.name).one_or_none()
    if secret is None:
        secret = Secret(name=payload.name, nonce=nonce, ciphertext=ciphertext)
        db.add(secret)
    else:
        secret.nonce = nonce
        secret.ciphertext = ciphertext
        secret.updated_at = utc_now()
    db.commit()
    return MessageResponse(name=payload.name, message="Secret saved")


@app.get("/secrets/{name}", response_model=SecretResponse, dependencies=[Depends(require_admin)])
def get_secret(name: str, db: Session = Depends(get_db)) -> SecretResponse:
    master_key = vault_state.require_unsealed()
    secret = db.query(Secret).filter(Secret.name == name).one_or_none()
    if secret is None:
        raise not_found("Secret not found")
    return SecretResponse(name=name, value=decrypt_secret(master_key, secret.nonce, secret.ciphertext))


@app.delete("/secrets/{name}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def delete_secret(name: str, db: Session = Depends(get_db)) -> MessageResponse:
    vault_state.require_unsealed()
    secret = db.query(Secret).filter(Secret.name == name).one_or_none()
    if secret is None:
        raise not_found("Secret not found")
    db.delete(secret)
    db.commit()
    return MessageResponse(name=name, message="Secret deleted")


@app.post("/secrets/{name}/wrap", response_model=WrapResponse, dependencies=[Depends(require_admin)])
def wrap_secret(
    name: str,
    payload: WrapRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WrapResponse:
    vault_state.require_unsealed()
    secret = db.query(Secret).filter(Secret.name == name).one_or_none()
    if secret is None:
        raise not_found("Secret not found")
    token, item = create_wrap_token(db, name, payload.ttl_seconds, settings)
    expires_at = normalize_utc(item.expires_at)
    return WrapResponse(token=token, expires_at=expires_at)


@app.post("/unwrap", response_model=SecretResponse)
def unwrap_secret(payload: UnwrapRequest, db: Session = Depends(get_db)) -> SecretResponse:
    master_key = vault_state.require_unsealed()
    token_hash = hash_token(payload.token)
    wrap = db.query(WrapToken).filter(WrapToken.token_hash == token_hash).one_or_none()
    if wrap is None:
        raise not_found("Token not found")
    if wrap.used:
        raise conflict("Token already used")
    if normalize_utc(wrap.expires_at) <= utc_now():
        raise gone("Token expired")
    secret = db.query(Secret).filter(Secret.name == wrap.secret_name).one_or_none()
    if secret is None:
        raise not_found("Secret not found")

    value = decrypt_secret(master_key, secret.nonce, secret.ciphertext)
    wrap.used = True
    wrap.used_at = utc_now()
    db.commit()
    return SecretResponse(name=secret.name, value=value)
