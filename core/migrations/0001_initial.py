import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import core.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("contact_person", models.CharField(max_length=120)),
                ("contact_email", models.EmailField(max_length=254)),
                ("contact_phone", models.CharField(max_length=20)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="company_logos/")),
                ("is_approved", models.BooleanField(default=False, help_text="Admin approves new companies before they can launch campaigns.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("target_url", models.URLField(help_text="Where the user is sent / what they view")),
                ("duration_seconds", models.PositiveIntegerField(default=30)),
                ("total_budget", models.DecimalField(decimal_places=2, max_digits=12)),
                ("cost_per_view", models.DecimalField(decimal_places=2, default=10.00, max_digits=8)),
                ("max_views", models.PositiveIntegerField(default=0, editable=False)),
                ("current_views", models.PositiveIntegerField(default=0)),
                ("payment_received", models.BooleanField(default=False, help_text="Admin confirms company payment manually.")),
                ("is_active", models.BooleanField(default=False)),
                ("expires_at", models.DateTimeField(blank=True, help_text="Optional. Campaign auto-hides after this date/time, even if views/budget remain. Leave blank to only limit by views.", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="campaigns", to="core.company")),
            ],
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(blank=True, max_length=20)),
                ("wallet_balance", models.DecimalField(decimal_places=2, default=0.00, max_digits=12)),
                ("is_email_verified", models.BooleanField(default=False)),
                ("is_suspected_bot", models.BooleanField(default=False, help_text="Flagged automatically by the anti-bot system; blocks withdrawals/earning until an admin clears it.")),
                ("last_ad_view_at", models.DateTimeField(blank=True, null=True)),
                ("signup_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="EmailOTP",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(default=core.models.gen_otp, max_length=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("consumed", models.BooleanField(default=False)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="otps", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AdView",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reward_amount", models.DecimalField(decimal_places=2, max_digits=8)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="views", to="core.campaign")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ad_views", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-completed_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="adview",
            unique_together={("user", "campaign")},
        ),
        migrations.CreateModel(
            name="WithdrawalRequest",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(choices=[("easypaisa", "Easypaisa"), ("jazzcash", "JazzCash")], max_length=20)),
                ("account_number", models.CharField(max_length=20)),
                ("account_name", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("admin_note", models.CharField(blank=True, max_length=255)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="withdrawals", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-requested_at"],
            },
        ),
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("entry_type", models.CharField(choices=[("credit", "Credit"), ("debit", "Debit")], max_length=10)),
                ("description", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
