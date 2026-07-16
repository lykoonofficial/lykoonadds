from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("verify-email/", views.verify_email, name="verify_email"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("ad/<int:ad_id>/watch/", views.watch_ad, name="watch_ad"),
    path("payout/<str:method>/", views.payout_method, name="payout_method"),
    path("withdrawals/", views.withdrawal_history, name="withdrawal_history"),
    path("campaign/create/", views.campaign_create, name="campaign_create"),
    path("offline/", views.offline, name="offline"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("sw.js", views.monetag_sw, name="monetag_sw"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("favicon.ico", views.favicon, name="favicon"),
]
