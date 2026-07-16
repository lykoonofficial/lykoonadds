import random

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Campaign, Company, WithdrawalRequest


class CaptchaMixin(forms.Form):
    """
    Simple in-house math captcha — no external API/key needed, works offline.
    The question is generated in the view and stored in the session; here we
    just validate what the user typed against it.
    """

    captcha_answer = forms.IntegerField(label="Security check", widget=forms.NumberInput(
        attrs={"placeholder": "Your answer", "autocomplete": "off"}
    ))

    def __init__(self, *args, expected_captcha=None, **kwargs):
        self.expected_captcha = expected_captcha
        super().__init__(*args, **kwargs)

    def clean_captcha_answer(self):
        value = self.cleaned_data["captcha_answer"]
        if self.expected_captcha is None or value != self.expected_captcha:
            raise ValidationError("Security check answer is wrong — please try again.")
        return value


def new_captcha_challenge():
    a, b = random.randint(2, 9), random.randint(2, 9)
    question = f"{a} + {b}"
    return question, a + b


class RegisterForm(CaptchaMixin):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    field_order = ["username", "email", "phone_number", "password1", "password2", "captcha_answer"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        return cleaned


class OTPVerifyForm(forms.Form):
    code = forms.CharField(max_length=6, label="6-digit code")


class WithdrawalForm(CaptchaMixin):
    method = forms.ChoiceField(choices=WithdrawalRequest.METHOD_CHOICES)
    account_number = forms.CharField(max_length=20, label="Mobile account number")
    account_name = forms.CharField(max_length=120, label="Account holder name")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=1)

    field_order = ["method", "account_number", "account_name", "amount", "captcha_answer"]

    def __init__(self, *args, wallet_balance=None, min_withdrawal=None, **kwargs):
        self.wallet_balance = wallet_balance
        self.min_withdrawal = min_withdrawal
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.min_withdrawal is not None and amount < self.min_withdrawal:
            raise ValidationError(f"Minimum withdrawal is {self.min_withdrawal} PKR.")
        if self.wallet_balance is not None and amount > self.wallet_balance:
            raise ValidationError("Amount exceeds your available wallet balance.")
        return amount


class CompanyCampaignForm(CaptchaMixin):
    """Companies submit this to request a new ad campaign. Goes live only
    after an admin manually confirms the company's payment was received."""

    company_name = forms.CharField(max_length=150)
    contact_person = forms.CharField(max_length=120)
    contact_email = forms.EmailField()
    contact_phone = forms.CharField(max_length=20)
    title = forms.CharField(max_length=200, label="Ad / Campaign title")
    description = forms.CharField(widget=forms.Textarea, required=False)
    target_url = forms.URLField(label="Ad link / video URL")
    duration_seconds = forms.IntegerField(min_value=5, max_value=600, initial=30)
    total_budget = forms.DecimalField(max_digits=12, decimal_places=2, min_value=1, label="Total budget (PKR)")
    cost_per_view = forms.DecimalField(max_digits=8, decimal_places=2, min_value=1, initial=10, label="Cost per view (PKR)")

    field_order = [
        "company_name", "contact_person", "contact_email", "contact_phone",
        "title", "description", "target_url", "duration_seconds",
        "total_budget", "cost_per_view", "captcha_answer",
    ]

    def save(self):
        company, _ = Company.objects.get_or_create(
            contact_email=self.cleaned_data["contact_email"],
            defaults={
                "name": self.cleaned_data["company_name"],
                "contact_person": self.cleaned_data["contact_person"],
                "contact_phone": self.cleaned_data["contact_phone"],
            },
        )
        campaign = Campaign.objects.create(
            company=company,
            title=self.cleaned_data["title"],
            description=self.cleaned_data.get("description", ""),
            target_url=self.cleaned_data["target_url"],
            duration_seconds=self.cleaned_data["duration_seconds"],
            total_budget=self.cleaned_data["total_budget"],
            cost_per_view=self.cleaned_data["cost_per_view"],
        )
        return campaign
