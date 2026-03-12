from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from datetime import timedelta

from apps.users.models.user import User
from apps.membersNsubscription.models import (
    Gym, UserGymRole, MembershipPlan, Subscription, Payment,
)
from apps.membersNsubscription.api.v1.serializers.subscription import (
    SubscriptionCreateSerializer,
    SubscriptionResponseSerializer,
    PaymentConfirmSerializer,
)


class SubscriptionCreateView(APIView):
    """
    POST /gyms/<gym_id>/subscriptions/

    Member subscribes to a plan.

    AC-1: PARTIAL UNIQUE — one active subscription per (gym, user)
    AC-2: Subscription.status = pending until payment confirmed
    AC-3: start_date set only when payment confirmed
    AC-4: session_pack → remaining_sessions = plan.session_limit
    AC-5: Payment record created with status=pending atomically
    AC-6: Notification fires on payment confirmation (see SubscriptionConfirmView)
    """

    @extend_schema(
        request=SubscriptionCreateSerializer,
        responses={
            201: SubscriptionResponseSerializer,
            400: OpenApiResponse(description='Validation error or already has active subscription.'),
            403: OpenApiResponse(description='Not an active member of this gym.'),
            404: OpenApiResponse(description='Gym, plan or user not found.'),
        },
        description=(
            'Subscribe to a membership plan. Creates a pending subscription and '
            'a pending payment record. Subscription activates after payment is confirmed.'
        )
    )
    @transaction.atomic
    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # ── Active member check ───────────────────────────────────────────────
        is_active_member = UserGymRole.objects.filter(
            gym=gym, user=user, status='active'
        ).exists()

        if not is_active_member:
            return Response(
                {'error': 'You must be an active member of this gym to subscribe.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── AC-1: one active subscription per (gym, user) ─────────────────────
        active_exists = Subscription.objects.filter(
            gym=gym,
            user=user,
            status=Subscription.Status.ACTIVE,
        ).exists()

        if active_exists:
            return Response(
                {'error': 'You already have an active subscription at this gym.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Also block duplicate pending subscriptions
        pending_exists = Subscription.objects.filter(
            gym=gym,
            user=user,
            status=Subscription.Status.PENDING if hasattr(Subscription.Status, 'PENDING') else 'pending',
        ).exists()

        if pending_exists:
            return Response(
                {'error': 'You already have a pending subscription awaiting payment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubscriptionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        plan_id        = serializer.validated_data['plan_id']
        payment_method = serializer.validated_data['payment_method']

        # ── Fetch plan scoped to this gym ─────────────────────────────────────
        plan = MembershipPlan.objects.filter(
            id=plan_id, gym=gym, is_active=True
        ).first()

        if not plan:
            return Response(
                {'error': 'Plan not found or not available at this gym.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── AC-4: session_pack remaining_sessions ─────────────────────────────
        remaining_sessions = None
        if plan.type == 'session_pack':
            if not plan.session_limit:
                return Response(
                    {'error': 'This session pack plan has no session limit configured.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            remaining_sessions = plan.session_limit

        # ── AC-2 + AC-3: status=pending, start_date=None until payment ────────
        subscription = Subscription.objects.create(
            gym                = gym,
            user               = user,
            plan               = plan,
            status             = 'pending',
            start_date         = timezone.now(),   # placeholder — updated on confirmation
            end_date           = None,
            remaining_sessions = remaining_sessions,
        )

        # ── AC-5: Payment record with status=pending ──────────────────────────
        payment = Payment.objects.create(
            gym          = gym,
            user         = user,
            subscription = subscription,
            amount       = plan.price,
            currency     = plan.currency,
            method       = payment_method,
            status       = 'pending',
        )

        return Response(
            {
                'message': 'Subscription created. Awaiting payment confirmation.',
                'subscription': SubscriptionResponseSerializer(subscription).data,
                'payment': {
                    'id':     str(payment.id),
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'method': payment.method,
                    'status': payment.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class SubscriptionConfirmView(APIView):
    """
    POST /gyms/<gym_id>/subscriptions/<subscription_id>/confirm/

    Admin confirms payment — activates subscription.

    AC-3: start_date = now (payment confirmed date)
    AC-6: Member notified on activation
    """

    @extend_schema(
        request=PaymentConfirmSerializer,
        responses={
            200: SubscriptionResponseSerializer,
            400: OpenApiResponse(description='Subscription not pending or payment already confirmed.'),
            403: OpenApiResponse(description='Admin only.'),
            404: OpenApiResponse(description='Subscription or payment not found.'),
        },
        description=(
            'Admin confirms payment for a pending subscription. '
            'Sets subscription to active, records start and end dates, '
            'and notifies the member.'
        )
    )
    @transaction.atomic
    def post(self, request, gym_id, subscription_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        # ── Admin check ───────────────────────────────────────────────────────
        if getattr(request, 'role', None) != 'admin':
            return Response(
                {'error': 'Only gym admins can confirm payments.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        subscription = Subscription.objects.filter(
            id=subscription_id, gym=gym
        ).select_related('plan', 'user').first()

        if not subscription:
            return Response({'error': 'Subscription not found.'}, status=status.HTTP_404_NOT_FOUND)

        if subscription.status != 'pending':
            return Response(
                {'error': 'Only pending subscriptions can be confirmed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # ── Confirm payment ───────────────────────────────────────────────────
        payment = Payment.objects.filter(
            subscription=subscription, status='pending'
        ).first()

        if not payment:
            return Response({'error': 'No pending payment found.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()

        payment.status    = 'completed'
        payment.reference = serializer.validated_data.get('reference', '')
        payment.save(update_fields=['status', 'reference'])

        # ── AC-3: start_date = confirmation date ──────────────────────────────
        end_date = now + timedelta(days=subscription.plan.duration_days) \
            if subscription.plan.duration_days else None

        subscription.status     = 'active'
        subscription.start_date = now
        subscription.end_date   = end_date
        subscription.save(update_fields=['status', 'start_date', 'end_date'])

        # ── AC-6: notify member ───────────────────────────────────────────────
        try:
            from apps.notifications.services import NotificationDispatcher
            from apps.notifications.models import NotificationLog

            NotificationDispatcher.dispatch(
                gym       = gym,
                user      = subscription.user,
                notif_type= 'general',
                channels  = [
                    NotificationLog.Channel.IN_APP,
                    NotificationLog.Channel.EMAIL,
                ],
                title   = 'Subscription Activated',
                message = (
                    f'Your {subscription.plan.name} subscription at {gym.name} '
                    f'is now active. '
                    + (f'Valid until {end_date.strftime("%Y-%m-%d")}.' if end_date else '')
                ),
            )
        except Exception:
            pass

        return Response(
            {
                'message': 'Payment confirmed. Subscription is now active.',
                'subscription': SubscriptionResponseSerializer(subscription).data,
            },
            status=status.HTTP_200_OK,
        )