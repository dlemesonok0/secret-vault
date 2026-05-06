from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit_event(db: Session, event_type: str, outcome: str, subject: str | None = None) -> None:
    db.add(AuditEvent(event_type=event_type, outcome=outcome, subject=subject))
    db.commit()
