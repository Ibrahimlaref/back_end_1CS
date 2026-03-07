import json
from django.utils import timezone
from .redis import redis_client
from django.shortcuts import get_object_or_404
from ..models.models import Course

class BehaviorEventService:
    EVENT_LIST_KEY='behavior_events'

    @classmethod
    def track(cls,gym,user,event_type,entity_type=None,entity_id=None,metadata=None):
        event={
            'gym':str(gym),
            'user':str(user),
            'event_type':event_type,
            'entity_type':entity_type or'',
            'entity_id':str(entity_id) if entity_id else None,
            'metadata':metadata or {},
            'occured_at':timezone.now().isoformat(),
        }

        redis_client.rpush(cls,EVENT_LIST_KEY,json.dumps(event))


