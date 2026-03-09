import logging

from apps.core.middleware.correlation import get_correlation_id, get_gym_id


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = get_correlation_id() or ""
        record.gym_id = get_gym_id() or ""
        return True
