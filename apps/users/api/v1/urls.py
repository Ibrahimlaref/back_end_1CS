from django.urls import path
from apps.users.api.v1.views.auth_views import (
    register_view,
    reset_password_view,
    verify_otp_view,
    resend_otp_view,
    login_view,
    logout_view,
    token_refresh_view,
    # 2FA
    verify_2fa_view,
    setup_2fa_view,
    confirm_2fa_view,
    disable_2fa_view,
    recover_2fa_view,
)
from apps.users.api.v1.views.user_views import (
    me_view,
    update_profile_view,
    update_account_view,
    change_password_view,
    delete_account_view,
)

urlpatterns = [

    # ── AUTH ──────────────────────────────────────────────────────────────────
    # Public — no token needed
    path('auth/register/',      register_view,      name='register'),
    path('auth/verify-otp/',    verify_otp_view,    name='verify-otp'),
    path('auth/resend-otp/',    resend_otp_view,    name='resend-otp'),
    path('auth/login/',         login_view,         name='login'),
    path('auth/refresh/',       token_refresh_view, name='token-refresh'),

    # Protected — token required
    path('auth/logout/',        logout_view,        name='logout'),

    # ── 2FA ───────────────────────────────────────────────────────────────────
    # Public (used during login flow, before token is issued)
    path('auth/2fa/verify/',    verify_2fa_view,    name='2fa-verify'),
    path('auth/2fa/recover/',   recover_2fa_view,   name='2fa-recover'),

    # Protected — token required
    path('auth/2fa/setup/',     setup_2fa_view,     name='2fa-setup'),
    path('auth/2fa/confirm/',   confirm_2fa_view,   name='2fa-confirm'),
    path('auth/2fa/disable/',   disable_2fa_view,   name='2fa-disable'),

    # ── USER ──────────────────────────────────────────────────────────────────
    # All protected — token required
    path('users/me/',           me_view,             name='me'),
    path('users/profile/',      update_profile_view, name='update-profile'),
    path('users/account/',      update_account_view, name='update-account'),
    path('users/password/',     change_password_view,name='change-password'),
    path('users/delete/',       delete_account_view, name='delete-account'),
]