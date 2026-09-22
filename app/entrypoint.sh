#!/bin/sh
set -e
echo "=== SCL startup: migrations + roles + staticfiles ==="
python manage.py migrate --noinput
python manage.py sync_roles
python manage.py collectstatic --noinput
echo "=== starting web ==="
exec python manage.py runserver 0.0.0.0:8000
