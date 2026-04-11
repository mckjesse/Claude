#!/bin/sh
#
# Container entrypoint.
#
# Runs database migrations then hands over to gunicorn. Migrations are
# idempotent so re-running on every start is safe for a single-instance
# web service. If this application ever scales to multiple replicas,
# move the migrate step into a Render pre-deploy command so only one
# process applies migrations at a time.
set -eu

echo "[entrypoint] running migrations"
python manage.py migrate --noinput

echo "[entrypoint] starting gunicorn"
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
