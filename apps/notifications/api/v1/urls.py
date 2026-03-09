from django.urls import path

from apps.notifications.api.v1.views.analytics import NotificationOpenRateAnalyticsView
from apps.notifications.api.v1.views.webhook import EmailDeliveryWebhookView

urlpatterns = [
    path("webhooks/email/", EmailDeliveryWebhookView.as_view(), name="notifications-email-webhook"),
    path("analytics/open-rates/", NotificationOpenRateAnalyticsView.as_view(), name="notifications-open-rates"),
]
