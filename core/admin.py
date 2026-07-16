from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Profile, Company, Campaign, AdView, WithdrawalRequest, LedgerEntry, EmailOTP


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet_balance", "is_email_verified", "is_suspected_bot", "created_at")
    list_filter = ("is_email_verified", "is_suspected_bot")
    search_fields = ("user__username", "user__email", "phone_number")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "contact_email", "is_approved", "created_at")
    list_filter = ("is_approved",)
    actions = ["approve_companies"]

    def approve_companies(self, request, queryset):
        queryset.update(is_approved=True)
    approve_companies.short_description = "Approve selected companies"


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "title", "company", "total_budget", "cost_per_view", "user_reward_display",
        "current_views", "max_views", "repeat_after_hours", "expiry_status", "payment_received", "is_active",
    )
    list_filter = ("payment_received", "is_active")
    search_fields = ("title", "company__name")
    actions = [
        "confirm_payment_and_activate", "deactivate",
        "expire_in_1_hour", "expire_in_12_hours", "expire_in_24_hours", "clear_expiry",
    ]

    def user_reward_display(self, obj):
        return f"{obj.user_reward} PKR"
    user_reward_display.short_description = "User reward/view"

    def expiry_status(self, obj):
        if not obj.expires_at:
            return "No time limit"
        if obj.is_expired:
            return format_html("<span style='color:#ef4444'>Expired ({})</span>", obj.expires_at.strftime("%d %b, %H:%M"))
        return obj.expires_at.strftime("%d %b, %H:%M")
    expiry_status.short_description = "Expires"

    def confirm_payment_and_activate(self, request, queryset):
        queryset.update(payment_received=True, is_active=True)
    confirm_payment_and_activate.short_description = "✅ Confirm payment received & activate campaign"

    def deactivate(self, request, queryset):
        queryset.update(is_active=False)
    deactivate.short_description = "Deactivate campaign"

    def _expire_in(self, queryset, **delta_kwargs):
        queryset.update(expires_at=timezone.now() + timezone.timedelta(**delta_kwargs))

    def expire_in_1_hour(self, request, queryset):
        self._expire_in(queryset, hours=1)
    expire_in_1_hour.short_description = "⏱ Auto-hide in 1 hour from now"

    def expire_in_12_hours(self, request, queryset):
        self._expire_in(queryset, hours=12)
    expire_in_12_hours.short_description = "⏱ Auto-hide in 12 hours from now"

    def expire_in_24_hours(self, request, queryset):
        self._expire_in(queryset, hours=24)
    expire_in_24_hours.short_description = "⏱ Auto-hide in 24 hours from now"

    def clear_expiry(self, request, queryset):
        queryset.update(expires_at=None)
    clear_expiry.short_description = "Remove time limit (only limit by views/budget)"


@admin.register(AdView)
class AdViewAdmin(admin.ModelAdmin):
    list_display = ("user", "campaign", "reward_amount", "ip_address", "completed_at")
    search_fields = ("user__username", "campaign__title")
    list_filter = ("completed_at",)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "status", "payout_details", "amount", "method",
        "user", "requested_at", "due_by",
    )
    list_filter = ("status", "method")
    search_fields = ("user__username", "account_number", "account_name")
    actions = ["mark_processing", "mark_completed", "mark_rejected"]

    def payout_details(self, obj):
        return format_html(
            "<strong>{}</strong><br><span style='font-family:monospace'>{}</span>",
            obj.account_name, obj.account_number,
        )
    payout_details.short_description = "Send money to (Name / Number)"

    def mark_processing(self, request, queryset):
        queryset.update(status="processing")
    mark_processing.short_description = "Mark as processing"

    def mark_completed(self, request, queryset):
        queryset.update(status="completed", processed_at=timezone.now())
    mark_completed.short_description = "✅ Mark completed (money actually sent!)"

    def mark_rejected(self, request, queryset):
        queryset.update(status="rejected", processed_at=timezone.now())
    mark_rejected.short_description = "❌ Reject (remember to refund wallet manually if needed)"


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "entry_type", "amount", "description", "created_at")
    list_filter = ("entry_type",)
    search_fields = ("user__username", "description")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "consumed", "created_at")
