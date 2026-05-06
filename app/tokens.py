from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import generate_token, hash_token
from app.models import WrapToken


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_wrap_token(
    db: Session,
    secret_name: str,
    ttl_seconds: int | None,
    settings: Settings,
) -> tuple[str, WrapToken]:
    ttl = ttl_seconds or settings.default_wrap_ttl_seconds
    ttl = min(ttl, settings.max_wrap_ttl_seconds)
    token = generate_token()
    item = WrapToken(
        token_hash=hash_token(token),
        secret_name=secret_name,
        expires_at=utc_now() + timedelta(seconds=ttl),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return token, item
