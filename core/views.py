from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models, transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .email_utils import send_otp_email
from .forms import (
    RegisterForm, OTPVerifyForm, WithdrawalForm, CompanyCampaignForm, new_captcha_challenge,
)
from .models import Campaign, AdView, WithdrawalRequest, EmailOTP, LedgerEntry


def _client_ip(request):
    return getattr(request, "client_ip", request.META.get("REMOTE_ADDR"))


def _new_captcha(request):
    question, answer = new_captcha_challenge()
    request.session["captcha_question"] = question
    request.session["captcha_answer"] = answer
    return question


# ---------------------------------------------------------------------------
# AUTH: register -> email OTP verification -> login
# ---------------------------------------------------------------------------
def register(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    captcha_question = request.session.get("captcha_question") or _new_captcha(request)

    if request.method == "POST":
        expected = request.session.get("captcha_answer")
        form = RegisterForm(request.POST, expected_captcha=expected)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
            )
            user.profile.phone_number = form.cleaned_data["phone_number"]
            user.profile.signup_ip = _client_ip(request)
            user.profile.save()

            otp = EmailOTP.objects.create(user=user)
            send_otp_email(
                to_email=user.email,
                subject="Your LykoonAdds verification code",
                message=f"Your verification code is: {otp.code}\nIt expires in {settings.OTP_EXPIRY_MINUTES} minutes.",
            )
            request.session["pending_verify_user_id"] = user.id
            request.session.pop("captcha_question", None)
            request.session.pop("captcha_answer", None)
            messages.info(request, "Account created! Enter the 6-digit code we emailed you to activate it.")
            return redirect("core:verify_email")
        else:
            captcha_question = _new_captcha(request)
    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form, "captcha_question": captcha_question})


def verify_email(request):
    user_id = request.session.get("pending_verify_user_id")
    if not user_id:
        return redirect("core:register")
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            otp = EmailOTP.objects.filter(user=user, code=code, consumed=False).order_by("-created_at").first()
            if otp is None:
                messages.error(request, "Invalid code.")
            elif otp.is_expired():
                messages.error(request, "Code expired — request a new one.")
            else:
                otp.consumed = True
                otp.save()
                user.profile.is_email_verified = True
                user.profile.save()
                auth_login(request, user)
                del request.session["pending_verify_user_id"]
                messages.success(request, "Email verified! Welcome to LykoonAdds.")
                return redirect("core:dashboard")
    else:
        form = OTPVerifyForm()

    return render(request, "core/verify_email.html", {"form": form, "email": user.email})


def resend_otp(request):
    user_id = request.session.get("pending_verify_user_id")
    if not user_id:
        return redirect("core:register")
    user = get_object_or_404(User, id=user_id)
    otp = EmailOTP.objects.create(user=user)
    send_otp_email(
        to_email=user.email,
        subject="Your LykoonAdds verification code",
        message=f"Your new verification code is: {otp.code}",
    )
    messages.info(request, "A new code has been sent.")
    return redirect("core:verify_email")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Let people log in with either their username or their email.
        username = identifier
        if "@" in identifier:
            matched_user = User.objects.filter(email__iexact=identifier).first()
            if matched_user:
                username = matched_user.username

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.profile.is_email_verified:
                request.session["pending_verify_user_id"] = user.id
                messages.warning(request, "Please verify your email first.")
                return redirect("core:verify_email")
            auth_login(request, user)
            return redirect("core:dashboard")
        messages.error(request, "Invalid username/email or password.")
    return render(request, "core/login.html")


def logout_view(request):
    auth_logout(request)
    return redirect("core:login")


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "core/home.html")

    profile = request.user.profile
    ads = list(
        Campaign.objects.filter(is_active=True, payment_received=True)
        .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()))
        .select_related("company")
        .order_by("-created_at")[:60]
    )

    # For each campaign the user has already done at least once, work out whether
    # it's locked forever (repeat_after_hours is None) or just on a cooldown
    # (repeat_after_hours is set) and, if so, when it unlocks again. We attach
    # the result straight onto each `ad` object so the template can read plain
    # attributes (ad.locked_forever / ad.hours_left) with no custom filters.
    last_views = {}
    for av in AdView.objects.filter(user=request.user, campaign__in=ads).order_by("completed_at"):
        last_views[av.campaign_id] = av.completed_at  # last one wins, thanks to ordering

    for ad in ads:
        ad.locked_forever = False
        ad.hours_left = None
        last_at = last_views.get(ad.id)
        if last_at:
            if ad.repeat_after_hours is None:
                ad.locked_forever = True
            else:
                unlocks_at = last_at + timedelta(hours=ad.repeat_after_hours)
                if timezone.now() < unlocks_at:
                    ad.hours_left = int((unlocks_at - timezone.now()).total_seconds() // 3600) + 1

    tasks_cleared = AdView.objects.filter(user=request.user).count()

    return render(
        request,
        "core/dashboard.html",
        {"profile": profile, "ads": ads, "tasks_cleared": tasks_cleared},
    )


@login_required
def watch_ad(request, ad_id):
    campaign = get_object_or_404(Campaign, id=ad_id, is_active=True, payment_received=True)

    last_view = AdView.objects.filter(user=request.user, campaign=campaign).order_by("-completed_at").first()
    if last_view:
        if campaign.repeat_after_hours is None:
            messages.info(request, "You already completed this task.")
            return redirect("core:dashboard")
        next_available_at = last_view.completed_at + timedelta(hours=campaign.repeat_after_hours)
        if timezone.now() < next_available_at:
            hours_left = int((next_available_at - timezone.now()).total_seconds() // 3600) + 1
            messages.info(request, f"You can do this task again in about {hours_left} hour(s).")
            return redirect("core:dashboard")

    if campaign.is_exhausted:
        messages.error(request, "This campaign has no slots left.")
        return redirect("core:dashboard")

    if request.method == "POST":
        # ---- Server-side anti-bot checks (never trust the client timer) ----
        started_raw = request.session.get(f"ad_start_{campaign.id}")
        if not started_raw:
            messages.error(request, "Task session expired — please start again.")
            return redirect("core:watch_ad", ad_id=ad_id)

        started_at = timezone.datetime.fromisoformat(started_raw)
        elapsed = (timezone.now() - started_at).total_seconds()
        if elapsed < campaign.duration_seconds:
            messages.error(request, "Task not completed yet — please wait for the full duration.")
            return redirect("core:watch_ad", ad_id=ad_id)

        profile = request.user.profile
        if profile.last_ad_view_at:
            gap = (timezone.now() - profile.last_ad_view_at).total_seconds()
            if gap < settings.AD_VIEW_COOLDOWN_SECONDS:
                profile.is_suspected_bot = True
                profile.save(update_fields=["is_suspected_bot"])
                messages.error(request, "Unusually fast activity detected — account flagged for review.")
                return redirect("core:dashboard")

        with transaction.atomic():
            if not campaign.register_view():
                messages.error(request, "This campaign just ran out of slots.")
                return redirect("core:dashboard")

            reward = campaign.user_reward
            AdView.objects.create(
                user=request.user,
                campaign=campaign,
                reward_amount=reward,
                ip_address=_client_ip(request),
                started_at=started_at,
            )
            profile.credit(reward, description=f"Reward for '{campaign.title}'")
            profile.last_ad_view_at = timezone.now()
            profile.save(update_fields=["last_ad_view_at"])

        del request.session[f"ad_start_{campaign.id}"]
        messages.success(request, f"+{reward} PKR credited to your wallet!")
        return redirect("core:dashboard")

    # GET — start the timer server-side
    request.session[f"ad_start_{campaign.id}"] = timezone.now().isoformat()
    return render(request, "core/watch_ad.html", {"campaign": campaign})


# ---------------------------------------------------------------------------
# PAYOUTS / WITHDRAWALS  (manual — see WithdrawalRequest docstring)
# ---------------------------------------------------------------------------
@login_required
def payout_method(request, method):
    if method not in dict(WithdrawalRequest.METHOD_CHOICES):
        messages.error(request, "Unknown payout method.")
        return redirect("core:dashboard")

    profile = request.user.profile
    captcha_question = request.session.get("captcha_question") or _new_captcha(request)

    if request.method == "POST":
        expected = request.session.get("captcha_answer")
        form = WithdrawalForm(
            request.POST, expected_captcha=expected,
            wallet_balance=profile.wallet_balance, min_withdrawal=Decimal(settings.MIN_WITHDRAWAL_PKR),
        )
        if profile.is_suspected_bot:
            messages.error(request, "Your account is under review — withdrawals are paused. Contact support.")
        elif form.is_valid():
            with transaction.atomic():
                profile.debit(form.cleaned_data["amount"], description="Withdrawal request (funds reserved)")
                WithdrawalRequest.objects.create(
                    user=request.user,
                    method=form.cleaned_data["method"],
                    account_number=form.cleaned_data["account_number"],
                    account_name=form.cleaned_data["account_name"],
                    amount=form.cleaned_data["amount"],
                )
            request.session.pop("captcha_question", None)
            request.session.pop("captcha_answer", None)
            messages.success(
                request,
                f"Withdrawal request submitted! You'll receive it within {settings.WITHDRAWAL_SLA_HOURS} hours.",
            )
            return redirect("core:withdrawal_history")
        else:
            captcha_question = _new_captcha(request)
    else:
        form = WithdrawalForm(
            initial={"method": method},
            wallet_balance=profile.wallet_balance, min_withdrawal=Decimal(settings.MIN_WITHDRAWAL_PKR),
        )

    return render(
        request, "core/payout_method.html",
        {"form": form, "method": method, "profile": profile, "captcha_question": captcha_question},
    )


@login_required
def withdrawal_history(request):
    withdrawals = WithdrawalRequest.objects.filter(user=request.user)
    return render(request, "core/withdrawal_history.html", {"withdrawals": withdrawals})


# ---------------------------------------------------------------------------
# COMPANY CAMPAIGNS (advertisers submit ads; admin confirms payment manually)
# ---------------------------------------------------------------------------
def campaign_create(request):
    captcha_question = request.session.get("captcha_question") or _new_captcha(request)

    if request.method == "POST":
        expected = request.session.get("captcha_answer")
        form = CompanyCampaignForm(request.POST, expected_captcha=expected)
        if form.is_valid():
            form.save()
            request.session.pop("captcha_question", None)
            request.session.pop("captcha_answer", None)
            messages.success(
                request,
                "Campaign submitted! It will go live once our team confirms your payment "
                "(you'll be contacted using the email/phone you provided).",
            )
            return redirect("core:campaign_create")
        else:
            captcha_question = _new_captcha(request)
    else:
        form = CompanyCampaignForm()

    return render(request, "core/campaign_create.html", {"form": form, "captcha_question": captcha_question})


# ---------------------------------------------------------------------------
# PWA support endpoints
# ---------------------------------------------------------------------------
def offline(request):
    return render(request, "core/offline.html")


def terms(request):
    return render(request, "core/terms.html")


def privacy(request):
    return render(request, "core/privacy.html")


def favicon(request):
    """Serves /favicon.ico from the app icon so browsers stop 404-ing on it."""
    icon_path = Path(settings.BASE_DIR) / "core" / "static" / "core" / "icons" / "icon-192.png"
    return HttpResponse(icon_path.read_bytes(), content_type="image/png")


def service_worker(request):
    """
    Served at the site ROOT (/service-worker.js), not under /static/, so its
    default scope covers the entire app instead of just /static/core/.
    """
    sw_path = Path(settings.BASE_DIR) / "core" / "static" / "core" / "service-worker.js"
    content = sw_path.read_text()
    response = HttpResponse(content, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def monetag_sw(request):
    """
    Verification file required by Monetag (ad network) — must be served at
    the site ROOT as /sw.js exactly, unrelated to our own PWA service worker.
    """
    sw_path = Path(settings.BASE_DIR) / "core" / "static" / "core" / "monetag-sw.js"
    content = sw_path.read_text()
    return HttpResponse(content, content_type="application/javascript")
