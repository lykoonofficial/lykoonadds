"""
LykoonAdds — Django settings.

IMPORTANT (read before deploying to production):
1. Change SECRET_KEY below to a new random value.
2. Set DEBUG = False in production.
3. Add your real domain to ALLOWED_HOSTS.
4. Switch DATABASES to Postgres/MySQL for real traffic (SQLite is fine for
   testing only).
5. Configure a real EMAIL backend (SMTP / SendGrid / etc.) so OTP emails
   actually get delivered — right now emails print to the console.
6. This project intentionally does NOT auto-transfer money to Easypaisa/
   JazzCash. Withdrawals are created as "pending" requests that an admin
   confirms manually after actually sending the money, because automated
   payouts require a registered payment/merchant account with SBP-licensed
   providers. See core/models.py -> WithdrawalRequest.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a .env file (if present) so things like your Gmail App
# Password work just by editing .env — no need to `export` anything by hand.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass  # missing/invalid .env or python-dotenv not installed — safe to continue

# ---------------------------------------------------------------------------
# CORE
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "change-this-to-a-real-random-secret-key-before-going-live-!!!",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RateLimitMiddleware",
]

ROOT_URLCONF = "lykoonadds.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_meta",
            ],
        },
    },
]

WSGI_APPLICATION = "lykoonadds.wsgi.application"
ASGI_APPLICATION = "lykoonadds.asgi.application"

# ---------------------------------------------------------------------------
# DATABASE  (swap for Postgres in production — see README)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    # Real persistent database (e.g. Railway/Render Postgres) — survives
    # every redeploy, unlike the local SQLite file below.
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    # Local development only — this file lives on disk and is fine for
    # testing, but gets wiped on every redeploy on most cloud platforms.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "core" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise serves static files directly from the app (CSS/JS/logo/PWA
# manifest/icons) without needing a separate nginx config — this is what
# makes `python manage.py collectstatic` + gunicorn work correctly on a
# real server out of the box.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"

# ---------------------------------------------------------------------------
# PERFORMANCE — "pro fast" (in-memory cache; swap for Redis in production)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "lykoonadds-cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# ---------------------------------------------------------------------------
# SECURITY — "pro secure"
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Only force HTTPS/HSTS once you actually have HTTPS configured, otherwise
# your site will lock itself out in dev. Toggle these to True in production.
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_FORCE_HTTPS", "False") == "True"
SESSION_COOKIE_SECURE = os.environ.get("DJANGO_FORCE_HTTPS", "False") == "True"
CSRF_COOKIE_SECURE = os.environ.get("DJANGO_FORCE_HTTPS", "False") == "True"
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_SSL_REDIRECT
SECURE_HSTS_PRELOAD = SECURE_SSL_REDIRECT

# Render/Railway both terminate HTTPS at a reverse proxy and forward plain
# HTTP internally, adding this header to say so. Without telling Django to
# trust it, SECURE_SSL_REDIRECT=True causes an infinite redirect loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# If you ever see "CSRF verification failed" on your live domain, set this
# env var to your full site URL, e.g. https://your-app.up.railway.app
_csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# EMAIL (for OTP verification) — replace with real SMTP creds in production
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = True
# Without this, a slow/blocked SMTP connection (common on some hosts) hangs
# the whole request until gunicorn's worker timeout kills it — crashing the
# page for the user. This makes it fail fast instead, so registration still
# completes even if the email can't be sent right away.
EMAIL_TIMEOUT = int(os.environ.get("DJANGO_EMAIL_TIMEOUT", "10"))

# Brevo (https://brevo.com) sends email over HTTPS instead of raw SMTP, so it
# still works even on hosts (like some Railway plans) that block outbound
# SMTP ports. If BREVO_API_KEY is set, it's used instead of the SMTP backend
# above. Leave blank to keep using plain SMTP.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_EMAIL_USER") or "LykoonAdds <no-reply@lykoonadds.com>"

# ---------------------------------------------------------------------------
# BUSINESS RULES (change freely — these drive the whole reward economy)
# ---------------------------------------------------------------------------
PLATFORM_CUT_PERCENT = 50          # LykoonAdds keeps this % of every ad view
USER_CUT_PERCENT = 50              # Users earn this % of every ad view
MIN_WITHDRAWAL_PKR = int(os.environ.get("MIN_WITHDRAWAL_PKR", "200"))
WITHDRAWAL_SLA_HOURS = 24           # promise shown to users — admin must honour it manually

# Set this via env var (e.g. G-XXXXXXXXXX) to see daily visitor stats in
# Google Analytics. Leave blank to disable tracking entirely.
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "")
AD_VIEW_COOLDOWN_SECONDS = 3         # anti-bot: min gap between two ad-view completions per user
OTP_EXPIRY_MINUTES = 10
