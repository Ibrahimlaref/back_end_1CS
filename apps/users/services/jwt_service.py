import uuid
import jwt
from datetime import timedelta
from django.utils import timezone
from django.conf import settings


# ─── GENERATE ─────────────────────────────────────────────────────────────────

def generate_tokens(user, gym_id, role):
    """
    Generates access + refresh token pair.

    Access token  → short lived (15 min), contains gym_id + role
    Refresh token → long lived (7 days), only contains user_id + jti

    Both share the same jti so we can revoke a session by jti.
    """
    jti = str(uuid.uuid4())
    now = timezone.now()

    access_payload = {
        'user_id': str(user.id),
        'gym_id':  str(gym_id) if gym_id is not None else None,
        'role':    role,
        'jwt_jti': jti,
        'type':    'access',
        'iat':     now.timestamp(),
        'exp':     (now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME_MINUTES)).timestamp(),
    }

    refresh_payload = {
        'user_id': str(user.id),
        'jwt_jti': jti,
        'type':    'refresh',
        'iat':     now.timestamp(),
        'exp':     (now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS)).timestamp(),
    }

    access_token  = jwt.encode(access_payload,  settings.JWT_SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET_KEY, algorithm='HS256')

    return {
        'access':  access_token,
        'refresh': refresh_token,
        'jti':     jti,
    }


# ─── DECODE ───────────────────────────────────────────────────────────────────

def decode_access_token(token):
    """
    Decodes and validates an access token.
    Returns the payload dict.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=['HS256'],
    )

    if payload.get('type') != 'access':
        raise jwt.InvalidTokenError("Not an access token.")

    return payload


def decode_refresh_token(token):
    """
    Decodes and validates a refresh token.
    Returns the payload dict.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=['HS256'],
    )

    if payload.get('type') != 'refresh':
        raise jwt.InvalidTokenError("Not a refresh token.")

    return payload


# ─── SESSION LOG ──────────────────────────────────────────────────────────────

def create_session(user, gym_id, jti, request=None):
    """
    Saves the session to SessionLog after generating tokens.
    Call this right after generate_tokens().
    """
    from apps.users.models.user import SessionLog

    ip      = None
    agent   = ''
    device  = ''

    if request:
        ip    = request.META.get('REMOTE_ADDR')
        agent = request.META.get('HTTP_USER_AGENT', '')
        device = _detect_device(agent)

    return SessionLog.objects.create(
        user=user,
        gym_id=gym_id,
        jwt_jti=jti,
        ip_address=ip,
        user_agent=agent,
        device_type=device,
    )


def revoke_session(jti):
    """Revoke a single session by jti."""
    from apps.users.models.user import SessionLog
    SessionLog.objects.filter(jwt_jti=jti).update(
        is_revoked=True,
        logged_out_at=timezone.now(),
    )


def revoke_all_sessions(user):
    """Revoke all active sessions for a user — used on password reset."""
    from apps.users.models.user import SessionLog
    SessionLog.objects.filter(
        user=user,
        is_revoked=False,
    ).update(
        is_revoked=True,
        logged_out_at=timezone.now(),
    )


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _detect_device(user_agent: str) -> str:
    ua = user_agent.lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'mobile'
    if 'tablet' in ua or 'ipad' in ua:
        return 'tablet'
    return 'desktop'













