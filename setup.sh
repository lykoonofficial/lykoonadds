#!/usr/bin/env bash
# One-command setup for LykoonAdds. Run this every time you extract a fresh
# copy of the project, or after pulling changes. Safe to re-run any time.
set -e

cd "$(dirname "$0")"

echo "==> Creating/activating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "==> Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "==> Building database tables (migrations)..."
python3 manage.py makemigrations core
python3 manage.py migrate

if [ ! -f ".env" ]; then
    echo "==> No .env found — copying .env.example (edit it later for Gmail OTP delivery)"
    cp .env.example .env
fi

echo ""
echo "==> Setup complete."
echo ""
if ! python3 manage.py shell -c "from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
    echo "No admin account exists yet. Let's create one now:"
    python3 manage.py createsuperuser
fi

echo ""
echo "==> Starting the server at http://127.0.0.1:8000/ (Ctrl+C to stop)"
python3 manage.py runserver
