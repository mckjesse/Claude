# FOXD Tender Pipeline — Backend

Django backend for the FOXD Tender Pipeline internal business app. The
frontend is a separate React application; this backend is the system of
record.

## Stack

- Python 3.12+
- Django 5.x
- Django REST Framework
- PostgreSQL
- django-filter, django-cors-headers
- Authentication: **SimpleJWT** (`djangorestframework-simplejwt`) as the
  primary path for the React frontend. Django session authentication is
  retained only for the Django admin and the DRF browsable API. No
  Entra/MSAL/Supabase.

## Project layout

```
config/            Django project (settings, urls, wsgi, asgi)
apps/users/        Custom AppUser model, auth endpoints
apps/pipeline/     Core domain models (companies, opportunities, quotes, ...)
```

## Local setup

1. **Create and activate a virtual environment** (Python 3.12+):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create a PostgreSQL database and role:**

   ```sql
   CREATE ROLE foxd WITH LOGIN PASSWORD 'foxd';
   CREATE DATABASE foxd_tender OWNER foxd;
   ```

4. **Copy the env template and edit values:**

   ```bash
   cp .env.example .env
   ```

   Set at least `SECRET_KEY`, `DB_*`, `CORS_ALLOWED_ORIGINS`, and
   `CSRF_TRUSTED_ORIGINS` to match your frontend origin.

5. **Run migrations:**

   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (first admin):**

   ```bash
   python manage.py createsuperuser
   ```

7. **Start the dev server:**

   ```bash
   python manage.py runserver
   ```

   The API is available at `http://localhost:8000/api/`, and the Django
   admin at `http://localhost:8000/admin/`.

## Auth endpoints

| Method | Path                          | Auth | Description |
|--------|-------------------------------|------|-------------|
| POST   | `/api/users/login/`           | none | Username/password. Returns `{access, refresh, user: {id, username, display_name, role}}`. No CSRF required |
| POST   | `/api/users/token/refresh/`   | refresh token | Exchanges a refresh token for a new access token |
| GET    | `/api/users/me/`              | required | Current user's profile. Works with `Bearer` or session |
| POST   | `/api/users/logout/`          | required | Ends the Django session if one exists. JWT clients simply discard their tokens |
| GET    | `/api/users/`                 | required | Active users, for estimator / assignee dropdowns |
| GET    | `/api/users/csrf/`            | none | Sets and returns the `csrftoken`. Only needed for session-based flows; JWT clients can ignore it |

Token lifetimes are set in `config/settings.py` under `SIMPLE_JWT`:
access **30 minutes**, refresh **7 days**, rotation enabled, header type
`Bearer`.

### React integration notes

1. `POST /api/users/login/` — store the `access` and `refresh` tokens.
2. Send `Authorization: Bearer <access>` on every subsequent request.
3. On a `401`, `POST /api/users/token/refresh/` with the refresh token
   and retry with the new access token.
4. **No CSRF cookie and no `X-CSRFToken` header are needed anywhere.**
5. `credentials: "include"` is **not** required — JWT auth is stateless
   and does not depend on cookies.
6. Ensure your React origin is listed in `CORS_ALLOWED_ORIGINS` in
   `.env`, so the browser permits the cross-origin call.

Why JWT rather than session cookies: session auth proved unreliable on
iPad Safari, whose cross-site cookie restrictions dropped the session
cookie. Bearer tokens are unaffected by cookie policy, which is what
makes the split between `crm.foxd.co` and `api.foxd.co` work at all.
`CSRF_TRUSTED_ORIGINS` still matters for the Django admin, which does use
session auth.

## User roles

`AppUser.role` (RBAC, enforced in views as features land):

- `director`
- `estimator`
- `project_manager`
- `admin`
- `read_only` (default)

## Seed demo data

```bash
python manage.py seed_demo           # idempotent, safe to re-run
python manage.py seed_demo --reset   # wipe pipeline data first
```

Creates five demo users (all with password `demo12345`): `director`,
`estimator1`, `estimator2`, `projects`, `officeadmin`. Plus realistic
Australian commercial fit-out sample data: 10 companies, 15 contacts,
25 opportunities across all stages, quotes, follow-ups, loss reasons,
and backdated activity logs. Seed uses a fixed random seed so each run
produces the same content.

## Tests

```bash
python manage.py test                # run the full suite
python manage.py test apps.pipeline  # scoped
```

The test database role needs `CREATEDB`:
```sql
ALTER ROLE foxd CREATEDB;
```

## Deployment (Render)

The backend ships as a Docker image. Render builds and runs it directly
from the repository.

### What the Dockerfile does

1. `pip install -r requirements.txt`
2. `collectstatic --noinput` at build time (WhiteNoise serves static
   files in production — no nginx, no CDN required for the Django admin
   or the DRF browsable API).
3. Copies the source and runs `entrypoint.sh` on container start.

### What `entrypoint.sh` does

1. `python manage.py migrate --noinput`
2. `exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers $WEB_CONCURRENCY`

Running migrations on container start is safe for a single-instance web
service. If you scale the service above one instance, move the migrate
step into a Render **pre-deploy command** so only one process applies
migrations per deploy.

### Required environment variables

| Variable | Required | Example | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | `...` | Long random string. Use Render's "Generate" button. |
| `DEBUG` | yes | `False` | Never `True` in production. |
| `ALLOWED_HOSTS` | yes | `foxd-backend.onrender.com,api.foxd.example` | Comma-separated. Include every hostname that resolves to the service. |
| `DATABASE_URL` | yes | *(auto)* | Render wires this automatically when you link a Postgres database to the service. |
| `CORS_ALLOWED_ORIGINS` | yes | `https://foxd.example.com` | Comma-separated React frontend origins. |
| `CSRF_TRUSTED_ORIGINS` | yes | `https://foxd.example.com` | Comma-separated. Needed for the session-authenticated Django admin, not for the JWT API. |
| `WEB_CONCURRENCY` | no | `3` | Gunicorn worker count. Default 3. |
| `PORT` | no | *(auto)* | Render injects this automatically. |

The discrete `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
variables from `.env.example` are **only** used when `DATABASE_URL` is
blank — they exist for local development convenience. Do not set them
on Render; just link a Postgres database and `DATABASE_URL` will be
provided.

### Recommended Render configuration

- **Service type**: Web Service
- **Environment**: Docker
- **Dockerfile path**: `./Dockerfile`
- **Health check path**: `/admin/login/` (returns 200 for unauthenticated
  GET)
- **Instance type**: start with the smallest paid tier; Render's free
  Postgres + free web service is fine for staging.
- **Pre-deploy command**: *(blank — entrypoint handles migrations)*
- **Start command**: *(blank — uses the Dockerfile `CMD`)*
- **Link a Render Postgres database** to the service so `DATABASE_URL`
  is populated automatically.

### Deployment checklist

Before clicking **Deploy**:

- [ ] `SECRET_KEY` set to a fresh random value (not the dev default).
- [ ] `DEBUG=False`.
- [ ] `ALLOWED_HOSTS` includes the Render hostname.
- [ ] Render Postgres database linked → `DATABASE_URL` visible in the
      service's environment.
- [ ] `CORS_ALLOWED_ORIGINS` includes the production React origin.
- [ ] `CSRF_TRUSTED_ORIGINS` includes the production React origin.
- [ ] React app sends `Authorization: Bearer <access>` and refreshes via
      `POST /api/users/token/refresh/` on 401.
- [ ] A superuser has been created — either via `render shell` then
      `python manage.py createsuperuser`, or by running `seed_demo`
      which creates predictable demo users.

### Local development unchanged

Everything in the **Local setup** section above still works exactly as
before. The Docker image is for production; `python manage.py runserver`
remains the local dev loop. Production security headers only switch on
when `DEBUG=False`, so HTTP cookies and non-HSTS behaviour stay intact
for local work.
