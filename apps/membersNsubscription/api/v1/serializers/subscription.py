from rest_framework import serializers
from apps.membersNsubscription.models import MembershipPlan, Subscription, Payment


class SubscriptionCreateSerializer(serializers.Serializer):
    """Request body to subscribe to a plan."""
    plan_id        = serializers.UUIDField()
    payment_method = serializers.ChoiceField(choices=[
        'cash', 'card', 'online', 'bank_transfer'
    ])


class PaymentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Payment
        fields = ['id', 'amount', 'currency', 'method', 'status', 'created_at']
        read_only_fields = fields


class SubscriptionResponseSerializer(serializers.ModelSerializer):
    payment = PaymentResponseSerializer(source='payments.first', read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'id', 'gym', 'user', 'plan', 'status',
            'start_date', 'end_date', 'remaining_sessions',
            'created_at', 'payment',
        ]
        read_only_fields = fields


class PaymentConfirmSerializer(serializers.Serializer):
    """Request body to confirm a payment (admin/cashier action)."""
    reference = serializers.CharField(required=False, allow_blank=True, default='')