from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from models.models import(
    Gym,
    Subscription,
    Reservation,
    AccessLog,
    MemberRetentionSignal,
)

class Command(BaseCommand):
    help='nightly job to calculate the risk score for every member to not coming back depending on the statistics of his logs and reservation'

    def handle (self ,*args,**kwargs):
        now=timezone.now()
        today=now.date()

        last_30=today-timedelta(days=30)
        prev_30_start=today-timedelta(days=60)
        prev_30_end=today-timedelta(days=31)

        self.stdout.write(f'[Churn Job] started at {now}')

        gyms=Gym.objects.filter(is_active=True)

        total_updated=0
        total_skipped=0

        for gym in gyms:
            paused_users_ids=Subscription.objects.filter(
                gym=gym,
                status=Subscription.status.PAUSED
            ).values_list('user_id',flat=True)

            active_users=Subscription.objects.filter(
                gym=gym,
                status=Subscription.status.ACTIVE
            ).exclude(
                user_id in paused_users_ids
            ).values_list('user_id',flat=True).distinct()

            if not active_users:
                continue

            for user_id in active_users:
                bookings_last_30_days=Reservation.objects,filter(
                    gym=gym,
                    user=user_id,
                    reserved_at__date=last_30,
                    status__in=[
                        Reservation.Status.RESERVED,
                        Reservation.Status.ATTENDED,
                    ]
                ).count()

                bookings_prev_30_days=Reservation.objects.filter(
                    gym=gym,
                    user=user_id,
                    reserved_at__date__range=(prev_30_start,prev_30_end),
                    status__in=[
                        Reservation.Status.RESERVED,
                        Reservation.Status.ATTENDED,
                    ]
                ).count()

                last_entry=AccessLog.objects.filter(
                    gym=gym,
                    user=user_id,
                    entry_type=AccessLog.EntryType.ENTRY
                ).order_by('-access_at').values_list('accessed_at',flat=True).first()

                if last_entry:
                    days_since_last_visit=(now-last_entry).days
                else:
                    days_since_last_visit=9999

                booking_drop=(
                    bookings_prev_30_days>0 and
                    bookings_last_30_days<bookings_prev_30_days*0.5
                )
                visit_gap_21=days_since_last_visit>=21
                visit_gap_45=days_since_last_visit>=45

                churn_risk_score=round(
                    (0.3 if booking_drop else 0)+
                    (0.3 if visit_gap_21 else 0)+
                    (0.4 if visit_gap_45 else 0),
                    4
                )

                
                if visit_gap_45:
                    signal=MemberRetentionSignal.Signal.CHURNED
                elif visit_gap_21:
                    signal=MemberRetentionSignal.Signal.CHURNING
                elif booking_drop:
                    signal=MemberRetentionSignal.Signal.AT_RISK
                else:
                    signal=MemberRetentionSignal.Signal.HEALTHY


                attended = Reservation.objects.filter(
                    gym=gym,
                    user_id=user_id,
                    reserved_at__date__gte=last_30,
                    status=Reservation.Status.ATTENDED
                ).count()

                attendance_rate = (
                    round(attended / bookings_last_30_days, 4)
                    if bookings_last_30_days > 0 else 0
                )

                MemberRetentionSignal.objects.update_or_create(
                    gym=gym.id,
                    user=user_id,
                    defaults={
                        "days_since_last_visit":days_since_last_visit,
                        "bookings_last_30_days":bookings_last_30_days,
                        "bookings_prev_30_days":bookings_prev_30_days,
                        "attendance_rate_last_30":attendance_rate,
                        "churn_risk_score":churn_risk_score,
                        "signal":signal,
                    }
                )


                total_updated+=1
        self.stdout.write(
            self.style.SUCCESS(
                f'[churn job] done. updated:{total_updated}|skipped(paused) {total_skipped}'
            )
        )