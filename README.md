# LykoonAdds

A Django-based "watch ads / complete tasks → earn PKR → withdraw to Easypaisa or
JazzCash" platform.

## What's included

- **Accounts**: register, login, logout, email OTP verification (6-digit code),
  math-captcha on all sensitive forms (register, withdraw, campaign submit).
- **Wallet & tasks**: users see active ad campaigns, complete a timed task,
  and get credited automatically. Server independently verifies the timer
  (never trusts the browser), and each user can only complete a given
  campaign once.
- **Company campaigns**: any business can submit a campaign (budget, cost per
  view, duration). **50% of the cost-per-view goes to the user, 50% stays
  with the platform** (configurable in `settings.py` via `PLATFORM_CUT_PERCENT`
  / `USER_CUT_PERCENT`). A campaign only goes live after an admin manually
  confirms the company's payment arrived (Django admin → Campaigns →
  "Confirm payment received & activate").
- **Withdrawals (manual, by design)**: user requests a withdrawal to
  Easypaisa/JazzCash; the amount is deducted from their wallet immediately
  (so it can't be double-spent) and appears in Django admin as "pending".
  You then send the real money yourself from your own Easypaisa/JazzCash
  app/account and click "Mark completed". The site promises a
  `WITHDRAWAL_SLA_HOURS` (default 24h) turnaround — that's on you to honour.
- **Anti-bot**: email OTP, math captcha, per-IP rate limiting, server-side
  timer checks, one-completion-per-user-per-campaign, and an
  `is_suspected_bot` flag that auto-freezes an account if it completes tasks
  suspiciously fast (cooldown configurable via `AD_VIEW_COOLDOWN_SECONDS`).
- **"Download the website" (installable PWA)**: a manifest + service worker
  let users install LykoonAdds as an app icon on their home screen / desktop
  from Chrome, Edge, or Safari — on **Android, Windows, Linux, and macOS** —
  with basic offline support. This is the realistic, working way to offer a
  cross-platform "download" without needing separate app-store builds. See
  the honest caveat below.
- **Security/perf defaults**: HttpOnly + SameSite cookies, clickjacking
  protection, HSTS/SSL toggles for production, cached sessions, and a cache
  layer ready to swap for Redis.

## Why withdrawals are manual, not automatic

Automatically pushing money into Easypaisa/JazzCash requires a **licensed
merchant/payment-service-provider account** regulated by the State Bank of
Pakistan — it's not something that can be wired up with just code and an API
key. This project deducts the wallet balance immediately on request (so
nothing can be double-withdrawn) and gives you, the admin, a clean queue in
Django admin to process payouts by hand from your own mobile wallet. Once you
have a real merchant account, you can replace the "mark completed" admin
action with a real API call.

## Honest note on the "download for Windows/Linux/mobile" app

What's shipped here is a **PWA (Progressive Web App)**: users tap "Download
App" (or their browser's "Install"/"Add to Home Screen"), and it installs as
a real app icon that opens full-screen, works offline for cached pages, and
runs on phones, laptops, and desktops — all from one codebase, today, with no
app-store review. This is genuinely the fastest and most maintainable route
for "one app, every platform."

What it is **not**: a native `.exe`, `.AppImage`, or Play Store `.apk` file.
If you specifically want those later:
- **Desktop (.exe/.dmg/.AppImage)**: wrap this same site in Electron or
  Tauri — a separate, smallish project once the web app is stable.
- **Mobile app store listing**: wrap it with Capacitor (or rebuild the UI in
  Flutter/React Native) to publish on Google Play / the App Store.
Both are optional next phases, not required for people to "install" the site
today.

## Get OTP codes delivered to real Gmail inboxes

By default OTP codes just print to your terminal (fine for testing). To make
them actually arrive in Gmail:

1. Turn on **2-Step Verification** on the Gmail account you'll send from:
   https://myaccount.google.com/security
2. Create an **App Password**: https://myaccount.google.com/apppasswords
   (App: "Mail", Device: "Other" → name it "LykoonAdds"). Google gives you a
   16-character code — that is NOT your normal Gmail password.
3. In the project folder, copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
4. Open `.env` and fill in:
   ```
   DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   DJANGO_EMAIL_HOST=smtp.gmail.com
   DJANGO_EMAIL_PORT=587
   DJANGO_EMAIL_USER=youraddress@gmail.com
   DJANGO_EMAIL_PASSWORD=the16charapppassword
   ```
5. Restart the server (`Ctrl+C` then `python manage.py runserver`). New OTP
   emails will now be sent from that Gmail address to whatever email the
   user registers with.

(`.env` is auto-loaded via `python-dotenv` — already in `requirements.txt`.)

## What's on the homepage now

Logged-out visitors hitting `/` now see a proper marketing landing page
(`core/templates/core/home.html`) — hero section, feature grid, "how it
works" steps, and a call-to-action — instead of being redirected straight to
the login form. Once logged in, the same URL shows the real dashboard.

## Compatibility notes (so nothing breaks on your machine)

- **Python version**: works on Python 3.10 through 3.13. `requirements.txt`
  uses flexible version ranges (not exact pins) so pip picks whichever
  release actually has a prebuilt wheel for your Python version — this is
  what caused the earlier "Pillow build failed" error on Python 3.13, and
  is now fixed.
- **Windows users**: `tzdata` is included in `requirements.txt` — without it,
  Django's timezone handling can fail on Windows (Windows doesn't ship the
  IANA timezone database that Linux/macOS have built in).
- **404 / 500 pages**: custom-branded error pages are included
  (`templates/404.html`, `templates/500.html`) so if something ever does go
  wrong in production (`DEBUG=False`), users see a clean page instead of a
  blank error.
- **Terms & Privacy**: real pages now exist at `/terms/` and `/privacy/`
  (linked from the footer) — useful before you invite real users, given
  money is involved.

## Fastest way to run this (one command)

Every time you extract a fresh copy of this project, just run:

```bash
chmod +x setup.sh
./setup.sh
```

This automatically: creates/activates the virtual environment, installs all
dependencies, builds the database tables, creates a `.env` if missing, asks
you to create an admin account if none exists, and starts the server. Safe
to run again any time — it won't duplicate anything that already exists.

## Troubleshooting

**`OperationalError: no such table: core_profile`** — the database tables
were never built in this copy of the project. This happens if you skip
`makemigrations`/`migrate` after extracting a fresh zip (very common when
re-extracting into a new folder or a new virtual environment). Fix:
```bash
python3 manage.py makemigrations core
python3 manage.py migrate
```
Or just run `./setup.sh`, which does this for you automatically every time.

**`Python-dotenv could not parse statement starting at line 1`** — this is
just a warning, not an error; it means one line in your `.env` file doesn't
look like `KEY=VALUE` (often from pasting with a text editor that adds
hidden characters). It doesn't stop the server from running, but if you
want it gone, recreate `.env` directly from the terminal:
```bash
cat > .env << 'EOF'
DJANGO_DEBUG=True
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USER=youraddress@gmail.com
DJANGO_EMAIL_PASSWORD=your16characterapppassword
EOF
```

## Deploying to Railway.app (no credit card needed)

Railway works like the Render walkthrough below, but doesn't require a card
to get started. This project includes `railway.json` and `start.sh` so
Railway auto-detects everything correctly.

### Step 1 — Push the code to GitHub
```bash
cd lykoonadds
git init
git add .
git commit -m "LykoonAdds"
```
Create an empty repo at https://github.com/new, then run the
`git remote add origin ...` / `git push` commands GitHub shows you.

### Step 2 — Create the Railway project
1. Go to https://railway.app and sign up/log in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select `lykoonadds`.
3. Railway detects Python via `railway.json` and starts building.

### Step 3 — Add environment variables
Open the **Variables** tab (use "Raw Editor" to paste all at once):
```
DJANGO_SECRET_KEY=<paste a long random string here>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=.up.railway.app
DJANGO_FORCE_HTTPS=True
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USER=lykoonofficial@gmail.com
DJANGO_EMAIL_PASSWORD=your16characterapppassword
DJANGO_SUPERUSER_USERNAME=lykoon
DJANGO_SUPERUSER_EMAIL=lykoonofficial@gmail.com
DJANGO_SUPERUSER_PASSWORD=<pick a strong admin password>
```
The last 3 lines auto-create your admin login on first start — no shell
access needed. Log into `/admin/` with them after deploy.

### Step 4 — Make the app publicly accessible
Service **Settings** → **Networking** → **Generate Domain**. You'll get a
URL like `https://lykoonadds-production.up.railway.app`.

### Step 5 — Visit your site
Open the generated URL — registration, Gmail OTP, tasks, wallet, and
withdrawals should all work. Log into `/admin/` with your
`DJANGO_SUPERUSER_*` credentials.

### Note on Railway's free tier
New accounts get a limited amount of free monthly usage before asking for a
card — normally enough for testing/demoing this project.

## Deploying to Render.com (needs a card for identity verification)

This project is fully set up for Render: it ships with **gunicorn**
(production server), **WhiteNoise** (serves CSS/JS/logo/PWA files with no
extra config needed), a `Procfile`, and a `render.yaml` blueprint that
auto-fills almost all settings for you.

### Step 1 — Put the code on GitHub (Render deploys from a Git repo)

```bash
cd ~/Desktop/lykoonadds
git init
git add .
git commit -m "LykoonAdds"
```
Then go to https://github.com/new, create a new **empty** repository (any
name, e.g. `lykoonadds`), and copy the commands it shows you, which look like:
```bash
git remote add origin https://github.com/YOUR-USERNAME/lykoonadds.git
git branch -M main
git push -u origin main
```
(`.env` is intentionally NOT pushed — see `.gitignore` — you'll re-enter
your Gmail credentials as Render environment variables in Step 3 instead,
which is safer than committing them to GitHub.)

### Step 2 — Create the Render service

1. Go to https://render.com and sign up (free) with your GitHub account.
2. Click **New +** → **Blueprint**.
3. Select your `lykoonadds` GitHub repo. Render will read `render.yaml`
   automatically and pre-fill the build command, start command, and most
   environment variables.
4. Click **Apply**.

### Step 3 — Fill in the 2 secrets Render can't guess

In the new service's **Environment** tab, set these two (left blank by
`render.yaml` on purpose, since they're private):
```
DJANGO_EMAIL_USER=lykoonofficial@gmail.com
DJANGO_EMAIL_PASSWORD=your16characterapppassword
```

### Step 4 — First deploy finishes → create your admin account

Once the deploy shows "Live", open the **Shell** tab for your service (or
use Render's web shell) and run:
```bash
python manage.py createsuperuser
```

### Step 5 — Visit your site

Render gives you a URL like `https://lykoonadds.onrender.com` — open it.
Registration, Gmail OTP, tasks, wallet, and withdrawals should all work
exactly like they did on your Kali machine.

### Important: SQLite doesn't survive redeploys on most platforms

The default database (`db.sqlite3`) lives on disk and gets wiped whenever
Render redeploys or restarts your free-tier service. That's fine for a
same-day demo/test. Before inviting real paying users, switch to a
**Postgres** database — Render gives you one free — by changing `DATABASES`
in `settings.py`. Tell me when you're ready and I'll wire it up.

### Free-tier note

Render's free web services "sleep" after 15 minutes of no traffic and take
~30-60 seconds to wake up on the next visit. This is normal and fine for
testing; upgrade to a paid instance later if you need it always-on.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser   # your admin login

python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the site and `http://127.0.0.1:8000/admin/`
for the admin panel (approve companies, activate campaigns, process
withdrawals).

OTP emails print to the console by default (`EMAIL_BACKEND` = console) so you
can test registration without a real mailbox. Set real SMTP credentials in
`.env` (copy `.env.example`) before going live.

## Before going live (checklist)

1. Set a real random `DJANGO_SECRET_KEY`.
2. `DJANGO_DEBUG=False`, add your real domain to `DJANGO_ALLOWED_HOSTS`.
3. Switch `DATABASES` in `settings.py` to Postgres/MySQL for real traffic.
4. Configure real SMTP so OTP codes actually get emailed.
5. Put this behind HTTPS and set `DJANGO_FORCE_HTTPS=True`.
6. Replace `django.core.cache.backends.locmem.LocMemCache` with Redis if you
   run more than one server process (rate limiting needs a shared cache).
7. Review `PLATFORM_CUT_PERCENT`, `MIN_WITHDRAWAL_PKR`, and
   `WITHDRAWAL_SLA_HOURS` in `settings.py` for your real business numbers,
   and make sure your ad-revenue/company-payments can actually sustain the
   payouts you're promising users.

## Project structure

```
lykoonadds/
├── manage.py
├── lykoonadds/            # project settings, root urls, wsgi/asgi
├── core/                  # the whole app: models, views, forms, admin
│   ├── models.py          # Profile, Company, Campaign, AdView, WithdrawalRequest, LedgerEntry, EmailOTP
│   ├── views.py           # auth, dashboard, watch_ad, payout, campaign_create
│   ├── middleware.py       # per-IP rate limiter
│   ├── templates/core/    # all pages
│   └── static/core/       # css, js, logo, PWA manifest/service-worker/icons
├── requirements.txt
└── .env.example
```
