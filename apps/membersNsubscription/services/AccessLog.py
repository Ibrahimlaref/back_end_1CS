from django.utils import timezone
from apps.membersNsubscription.models.models import (AccessLog,UserGymRole,Subscription,Notification,MemberRetentionSignal)

def handle_gym_scan(gym,user,entry_type,method,device_id=""):
#check if memeber is suspended
    role=UserGymRole.objects.filter(
        gym=gym,
        user=user,
        role=UserGymRole.Role.MEMBER
    ).first()

    if not role or role.status ==UserGymRole.Status.SUSPENDED:
        #notify all admins of the gym
        admins=UserGymRole.objects.filter(
            gym=gym,
            role=UserGymRole.Role.ADMIN,
            status=UserGymRole.Status.ACTIVE
        )
        for admin in admins:
            Notification.objects.create(
                gym=gym,
                user=admin.user,
                type=Notification.Type.GENERAL,
                title="suspended member scan attempt",
                message=f'user {user} attemepted to scan in but is suspended'
            )
        return{"allowed":False,"reason":"suspended"}
    
    #check if subsecription is active
    active_sub=Subscription.objects.filter(
        gym=gym,
        user=user,
        status=Subscription.Status.ACTIVE
    ).first()

    if not active_sub:
        #notify the memeber to renew
        Notification.objects.create(
            gym=gym,
            user=user,
            type=Notification.Type.SUBSCRIPTION_RENEWAL,
            title='subscription expired',
            message="your subscription has expired, please renew to access the gym"
        )
        return{"allowed":False,"reason":"expired_subscription"}
    
    #all good, log the access

    AccessLog.objects.create(
        gym=gym,
        user=user,
        entry_type=entry_type,
        method=method,
        device_id=device_id
    )

    #update rentention signal
    if entry_type==AccessLog.EntryType.ENTRY:
        _update_retention_signal(gym,user)
    return{"allowed":True}


def _update_retention_signal(gym,user):
    now=timezone.now()
    thirty_days_ago=now-timezone.timedelta(days=30)

    recents_visits=AccessLog.objects.filter(
        gym=gym,
        user=user,
        entry_type=AccessLog.EntryType.ENTRY,
        accessed_at__gte=thirty_days_ago
    ).count()

    signal,_=MemberRetentionSignal.objects.get_or_create(
        gym=gym,
        user=user,
        defaults={"signal":MemberRetentionSignal.Signal.HEALTHY}
    )

    signal.days_since_last_visit=0
    signal.bookings_last_30_days=recents_visits

    if recents_visits>=8:
        signal.signal=MemberRetentionSignal.Signal.HEALTHY
        signal.churn_risk_score=0.1
    elif recents_visits>=4:
        signal.signal=MemberRetentionSignal.Signal.AT_RISK
        signal.churn_risk_score=0.5
    else:
        signal.signal=MemberRetentionSignal.Signal.CHURNING
        signal.churn_risk_score=0.8
    
    signal.save()