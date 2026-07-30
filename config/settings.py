"""
Django settings for the FOXD Tender Pipeline backend.

Single-file settings, driven by environment variables loaded from a .env
file beside manage.py via python-dotenv. Production hardening is gated
on DEBUG=False so local development is unaffected.
"""
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _csv(value: str) -> list[str]:
    """
    Split a comma-separated env value into a list, stripping whitespace
    and any trailing slash from each item. Trailing slashes are a common
    copy-paste artefact that silently break Django's exact-match origin
    comparison for CORS and CSRF.
    """
    return [
        item.strip().rstrip("/")
        for item in value.split(",")
        if item.strip()
    ]


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ALLOWED_HOSTS is a comma-separated list of *hostnames only* — no
# scheme, no path (e.g. "foxd.onrender.com,api.example.com").
ALLOWED_HOSTS = _csv(os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1"))

# Known FOXD production backend hostnames. Merged in as a baseline so
# the service always answers on its production domain and its current
# Render URL, even if the ALLOWED_HOSTS env var drifts or is not set.
# The Render URL is kept deliberately during the domain cutover.
_BASELINE_ALLOWED_HOSTS = [
    "api.foxd.co",
    "crm-backend-pza6.onrender.com",
]
for _host in _BASELINE_ALLOWED_HOSTS:
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

# Render injects RENDER_EXTERNAL_HOSTNAME automatically for every web
# service (e.g. "foxd-backend.onrender.com"). Adding it here means the
# service responds correctly on its Render URL without having to list
# the hostname manually in the dashboard. The variable is only set on
# Render, so local development is unaffected.
_RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _RENDER_HOST and _RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_RENDER_HOST)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "apps.users",
    "apps.pipeline",
]

MIDDLEWARE = [
    # CorsMiddleware must sit at the very top so CORS headers are
    # attached to every response, including redirects from
    # SecurityMiddleware and static files served by WhiteNoise.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files in production. Must come right after
    # SecurityMiddleware and before any middleware that might serve
    # responses.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
#
# Production (Render) provides DATABASE_URL when a Postgres instance is
# linked to the service; parsing that takes precedence. If DATABASE_URL
# is unset or unparseable we fall back to the discrete DB_* variables
# used for local development.
# ---------------------------------------------------------------------------
_db_from_url = dj_database_url.config(
    default="",
    conn_max_age=600,
    ssl_require=not DEBUG,
)
if _db_from_url:
    DATABASES = {"default": _db_from_url}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "foxd_pipeline"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

AUTH_USER_MODEL = "users.AppUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Session auth kept so the Django admin and browsable API still
        # work. JWT is the primary path for the React frontend.
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "config.renderers.FoxdJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 25,
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

# The React frontend authenticates purely with these stateless JWTs,
# sent in the `Authorization: Bearer <access>` header on every request
# and refreshed via POST /api/users/token/refresh/. This path does NOT
# use or depend on the Django session / csrftoken cookies, so it works
# identically regardless of the browser's cross-site cookie policy —
# which is exactly what we need for crm.foxd.co calling api.foxd.co.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# CORS / CSRF for a separate React frontend
# ---------------------------------------------------------------------------
# Production frontend origins that must always be allowed, merged on
# top of anything supplied via the env var. crm.foxd.co is the new
# production frontend; the Lovable origin is kept TEMPORARILY during
# the cutover and can be dropped from this list once traffic has fully
# moved to crm.foxd.co.
_BASELINE_FRONTEND_ORIGINS = [
    "https://crm.foxd.co",
    "https://foxd-crm.lovable.app",  # temporary — remove post-cutover
]

CORS_ALLOWED_ORIGINS = _csv(
    os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
)
for _origin in _BASELINE_FRONTEND_ORIGINS:
    if _origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(_origin)

# CORS_ALLOW_CREDENTIALS stays on so the Django admin / browsable API
# (session + cookie based) keep working. The React frontend authenticates
# with stateless JWT Bearer tokens and does not depend on this.
CORS_ALLOW_CREDENTIALS = True

# CSRF_TRUSTED_ORIGINS is a comma-separated list of *full origins* —
# scheme + host (e.g. "https://foxd.onrender.com,https://foxd.example").
# Only relevant to session/cookie POSTs (admin, browsable API); the JWT
# frontend does not need CSRF. The production frontend origins are merged
# in so those flows keep working during and after the cutover.
CSRF_TRUSTED_ORIGINS = _csv(
    os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
)
for _origin in _BASELINE_FRONTEND_ORIGINS:
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)
if _RENDER_HOST:
    _render_origin = f"https://{_RENDER_HOST}"
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

# React must be able to read the csrftoken cookie to echo it in the
# X-CSRFToken header, so this one is not HttpOnly.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

# Cross-site session auth: the frontend (foxd-crm.lovable.app) and the
# backend (crm-backend-pza6.onrender.com) live on different domains, so
# the browser will only store and send the session + csrftoken cookies
# when SameSite=None is combined with Secure=True. Set unconditionally
# so the cookie policy does not depend on DEBUG being flipped correctly
# at deploy time.
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

# Explicitly leave the cookie Domain attribute unset. With Domain=None
# the browser scopes the cookie to the exact host that set it (the
# backend's Render hostname), which is what we want for cross-site
# session auth. Setting Domain to anything else — or letting a stale
# env var override this — makes the browser silently drop the cookie.
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None

# ---------------------------------------------------------------------------
# Production hardening
#
# Only applied when DEBUG is off so local development over plain HTTP
# keeps working.
# ---------------------------------------------------------------------------
if not DEBUG:
    # Render (and most PaaS) terminate TLS at the edge and forward the
    # original scheme via this header. Without it, Django sees http://
    # and refuses to set secure cookies.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_HSTS_SECONDS = 60 * 60  # 1 hour — bump once validated in prod
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False

    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
