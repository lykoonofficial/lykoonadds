import random
import string
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.utils import timezone


def gen_otp():
    return "".join(random.choices(string.digits, k=6))


class Profile(models.Model):
    """Extra data attached to every registered user (wallet, verification, anti-bot state)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=20, blank=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_email_verified = models.BooleanField(default=False)
    is_suspected_bot = models.BooleanField(
        default=False, help_text="Flagged automatically by the anti-bot system; blocks withdrawals/earning until an admin clears it."
    )
    last_ad_view_at = models.DateTimeField(null=True, blank=True)
    signup_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"

    def credit(self, amount: Decimal, description: str):
        amount = Decimal(amount)
        self.wallet_balance = self.wallet_balance + amount
        self.save(update_fields=["wallet_balance"])
        LedgerEntry.objects.create(
            user=self.user, amount=amount, entry_type=LedgerEntry.CREDIT, description=description
        )

    def debit(self, amount: Decimal, description: str):
        amount = Decimal(amount)
        if amount > self.wallet_balance:
            raise ValueError("Insufficient balance")
        self.wallet_balance = self.wallet_balance - amount
        self.save(update_fields=["wallet_balance"])
        LedgerEntry.objects.create(
            user=self.user, amount=amount, entry_type=LedgerEntry.DEBIT, description=description
        )


class EmailOTP(models.Model):
    """One-time code used to verify a new account's email — core anti-bot gate #1."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6, default=gen_otp)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed = models.BooleanField(default=False)

    def is_expired(self):
        age = timezone.now() - self.created_at
        return age.total_seconds() > settings.OTP_EXPIRY_MINUTES * 60

    def __str__(self):
        return f"OTP({self.user.username})"


class Company(models.Model):
    """A business/advertiser account that pays to run campaigns on the platform."""

    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=120)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    is_approved = models.BooleanField(default=False, help_text="Admin approves new companies before they can launch campaigns.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Campaign(models.Model):
    """
    An ad a company wants users to watch/interact with.

    Money flow (manual, not an automated payment gateway):
      1. Company agrees a total_budget with LykoonAdds off-platform and submits this form.
      2. Admin marks payment_received once the company's payment has actually arrived.
      3. Only then does is_active flip on and users can start earning from it.

    Per view: cost_per_view is split PLATFORM_CUT_PERCENT / USER_CUT_PERCENT
    (50/50 by default, configurable in settings.py).
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="campaigns")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_url = models.URLField(help_text="Where the user is sent / what they view")
    duration_seconds = models.PositiveIntegerField(default=30)
    total_budget = models.DecimalField(max_digits=12, decimal_places=2)
    cost_per_view = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("10.00"))
    max_views = models.PositiveIntegerField(editable=False, default=0)
    current_views = models.PositiveIntegerField(default=0)
    payment_received = models.BooleanField(default=False, help_text="Admin confirms company payment manually.")
    is_active = models.BooleanField(default=False)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Optional. Campaign auto-hides after this date/time, even if views/budget remain. Leave blank to only limit by views.",
    )
    repeat_after_hours = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=(
            "Kitne ghante baad ek user isi task ko dobara complete kar sakta hai. "
            "Khaali chhodain agar yeh task har user sirf EK BAAR (hamesha ke liye) complete kar sake, kabhi reset na ho."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.cost_per_view and self.total_budget:
            self.max_views = int(self.total_budget // self.cost_per_view)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.company.name})"

    @property
    def user_reward(self):
        pct = Decimal(settings.USER_CUT_PERCENT) / Decimal(100)
        return (self.cost_per_view * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def platform_cut(self):
        pct = Decimal(settings.PLATFORM_CUT_PERCENT) / Decimal(100)
        return (self.cost_per_view * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def slots_remaining(self):
        return max(self.max_views - self.current_views, 0)

    @property
    def is_expired(self):
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    @property
    def is_exhausted(self):
        return self.slots_remaining <= 0 or self.is_expired

    def register_view(self):
        """Atomically consume one slot. Returns False if nothing left or expired."""
        if self.is_expired:
            return False
        updated = Campaign.objects.filter(pk=self.pk, current_views__lt=models.F("max_views")).update(
            current_views=models.F("current_views") + 1
        )
        return updated == 1


class AdView(models.Model):
    """Records that a specific user completed a specific campaign — prevents double-claiming."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ad_views")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="views")
    reward_amount = models.DecimalField(max_digits=8, decimal_places=2)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.campaign.title}"


class WithdrawalRequest(models.Model):
    """
    A user's request to cash out their wallet balance.

    This is intentionally MANUAL: the site does not hold a licensed money-
    transmission integration with Easypaisa/JazzCash. When a request comes
    in, the wallet amount is deducted immediately (so it can't be spent
    twice) and an admin sends the real money by hand, then marks it
    completed. Promise to users: processed within WITHDRAWAL_SLA_HOURS.
    """

    METHOD_CHOICES = [
        ("easypaisa", "Easypaisa"),
        ("jazzcash", "JazzCash"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawals")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.CharField(max_length=255, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.user.username} — {self.amount} PKR via {self.method} [{self.status}]"

    def due_by(self):
        return self.requested_at + timezone.timedelta(hours=settings.WITHDRAWAL_SLA_HOURS)


class LedgerEntry(models.Model):
    """Every wallet credit/debit — powers the activity feed and gives a full audit trail."""

    CREDIT = "credit"
    DEBIT = "debit"
    TYPE_CHOICES = [(CREDIT, "Credit"), (DEBIT, "Debit")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ledger_entries")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.entry_type == self.CREDIT else "-"
        return f"{sign}{self.amount} — {self.description}"
