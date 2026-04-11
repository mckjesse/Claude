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
- Authentication: Django native **session authentication** only (no JWT,
  no token auth, no Entra/MSAL/Supabase)

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

| Method | Path                 | Description                              |
|--------|----------------------|------------------------------------------|
| GET    | `/api/users/me/`     | Current user + sets CSRF cookie          |
| POST   | `/api/users/login/`  | Username/password login, starts session  |
| POST   | `/api/users/logout/` | Ends the session                         |

### React integration notes

- The React app must send requests with `credentials: "include"` so
  session and CSRF cookies flow.
- On app load, React should call `GET /api/users/me/` once. This sets
  the `csrftoken` cookie and tells the frontend whether the user is
  already signed in (200 vs 401).
- For any unsafe method (POST/PUT/PATCH/DELETE), React must read the
  `csrftoken` cookie and send it in the `X-CSRFToken` header.
- Ensure your React dev origin is listed in both `CORS_ALLOWED_ORIGINS`
  and `CSRF_TRUSTED_ORIGINS` in `.env`.

## User roles

`AppUser.role` (RBAC, enforced in views as features land):

- `director`
- `estimator`
- `project_manager`
- `admin`
- `read_only` (default)
