#!/usr/bin/env bash
# Unified production start script — used by both Render and Railway.
# Safe to run on every deploy: migrations and admin-account creation are
# both idempotent (they skip cleanly if already done).
set -e

if [ -z "$DATABASE_URL" ]; then
  echo ""
  echo "############################################################"
  echo "# WARNING: DATABASE_URL is not set!"
  echo "# You are running on temporary SQLite storage — ALL users,"
  echo "# wallets, and campaigns will be WIPED on the next deploy."
  echo "# Add a Postgres database and set DATABASE_URL to fix this"
  echo "# permanently. See README.md -> 'Permanent database setup'."
  echo "############################################################"
  echo ""
else
  echo "==> DATABASE_URL is set — using persistent database. Good."
fi

echo "==> Generating any missing migrations..."
python manage.py makemigrations core --noinput

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Ensuring admin account exists (if DJANGO_SUPERUSER_* vars are set)..."
python manage.py ensure_superuser

echo "==> Starting gunicorn..."
exec gunicorn lykoonadds.wsgi --log-file - --timeout 30 --bind 0.0.0.0:${PORT:-8000}
