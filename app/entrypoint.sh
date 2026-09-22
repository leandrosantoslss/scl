#!/bin/sh
set -e
echo "=== SCL startup: migrations + roles + staticfiles ==="
python manage.py migrate --noinput
python manage.py sync_roles
python manage.py collectstatic --noinput
echo "=== starting web ==="
exec gunicorn app.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
