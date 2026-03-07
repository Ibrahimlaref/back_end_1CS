from ..models.models import AuditLog

def log_action(
        *,
        actor,
        action,
        target,
        gym=None,
        old_values=None,
        new_values=None,
        request=None,
):
    ip=None
    ua=""
    if request:
        X_fowarded=request.META.get("HTTP_X_FOWARDED_FOR")
        ip=X_fowarded.split(",")[0].strip() if X_fowarded else request.META.get("REMOTE_ADDR")
        ua=request.META.get("HTTP_USER_AGENT","")

    AuditLog.objects.create(    
        actor=actor,
        gym=gym,
        target_id=target.pk,
        target_table=target._META.db_table,
        action=action,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip,
        user_agent=ua,
    )