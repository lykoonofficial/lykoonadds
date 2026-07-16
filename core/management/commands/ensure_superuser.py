import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Creates a superuser from DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD
    environment variables, but only if that username doesn't already exist.
    Safe to run on every deploy/start — it never errors out or duplicates.

    This lets platforms without easy interactive shell access (like a
    Railway free-tier deploy) still get an admin account automatically.
    """

    help = "Creates an admin account from env vars if it doesn't already exist."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD not set — skipping admin auto-create.")
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin '{username}' already exists — skipping.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin account '{username}'."))
