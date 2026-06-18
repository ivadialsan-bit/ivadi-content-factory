from models import AuditLog


def log_event(
    db,
    action: str,
    user=None,
    tenant_id=None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    try:
        log = AuditLog(
            tenant_id=tenant_id if tenant_id is not None else getattr(user, "tenant_id", None),
            user_id=getattr(user, "id", None),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"AUDIT_LOG_ERROR: {action}: {e}")
