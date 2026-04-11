# syntax=docker/dockerfile:1
#
# FOXD Tender Pipeline backend — production image
#
# Single-stage image built on python:3.12-slim. psycopg[binary] brings its
# own libpq so we do not need libpq-dev from apt. Static files are
# collected at build time; migrations and gunicorn are handled by the
# entrypoint script at container start.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install Python dependencies first so Docker layer caching works well.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the rest of the project.
COPY . .

# Collect static files into STATIC_ROOT at build time. collectstatic does
# not touch the database, but the settings module must import cleanly —
# so we pass a throwaway SECRET_KEY just for the build step.
RUN SECRET_KEY=build-time-placeholder DEBUG=False \
    python manage.py collectstatic --noinput

RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
