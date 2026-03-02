from django.urls import path
from apps.users.api.v1.views.auth_views import (
    register_view,
    verify_otp_view,
    resend_otp_view,
    login_view,
    logout_view,
    token_refresh_view,
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
    path('auth/register/',   register_view,       name='register'),
    path('auth/verify-otp/', verify_otp_view,     name='verify-otp'),
    path('auth/resend-otp/', resend_otp_view,     name='resend-otp'),
    path('auth/login/',      login_view,          name='login'),
    path('auth/refresh/',    token_refresh_view,  name='token-refresh'),

    # Protected — token required
    path('auth/logout/',     logout_view,         name='logout'),

    # ── USER ──────────────────────────────────────────────────────────────────
    # All protected — token required
    path('users/me/',        me_view,             name='me'),
    path('users/profile/',   update_profile_view, name='update-profile'),
    path('users/account/',   update_account_view, name='update-account'),
    path('users/password/',  change_password_view,name='change-password'),
    path('users/delete/',    delete_account_view, name='delete-account'),

]