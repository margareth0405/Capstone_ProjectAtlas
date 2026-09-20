"""Django settings for ATLAS using PostgreSQL."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# The Xet transport can stall on some Windows networks. Prefer the standard
# resumable HTTP path unless an operator explicitly opts back into Xet.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-atlas-development-only")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

ADMIN_URL_PATH = os.getenv("DJANGO_ADMIN_PATH", "").strip().strip("/")
if not ADMIN_URL_PATH:
    raise ImproperlyConfigured(
        "DJANGO_ADMIN_PATH is required. Configure a private admin path in .env."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    "allauth",
    "allauth.account",

    "library.apps.LibraryConfig",

]
SITE_ID = 1

if DEBUG:
    INSTALLED_APPS.append('django_browser_reload')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "library.middleware.RateLimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "library.middleware.WebsiteUsageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(4, "django_browser_reload.middleware.BrowserReloadMiddleware")

ROOT_URLCONF = "atlas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "library.context_processors.atlas_navigation",
            ],
        },
    }
]

WSGI_APPLICATION = "atlas.wsgi.application"
ASGI_APPLICATION = "atlas.asgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL is required. Configure a PostgreSQL connection in .env."
    )

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "60")),
        conn_health_checks=True,
        ssl_require=env_bool("DB_SSL_REQUIRE", not DEBUG),
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Manila")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedStaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        )
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "library:login"
LOGIN_REDIRECT_URL = "library:dashboard"
LOGOUT_REDIRECT_URL = "library:landing"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# django-allauth owns account identity, email verification, and recovery while
# ATLAS keeps its role-aware login and registration screens.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = os.getenv(
    "ACCOUNT_EMAIL_VERIFICATION", "optional"
).strip().lower()
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = False

EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "ATLAS <noreply@atlas.local>")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "atlastshs@gmail.com")
SUPPORT_HOURS = os.getenv("SUPPORT_HOURS", "Monday–Friday, 8:00 AM–5:00 PM")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "").strip()
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(
    os.getenv("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_REFERRER_POLICY = "same-origin"
CSRF_FAILURE_VIEW = "library.views.errors.csrf_failure"

# Fixed-window limits protect expensive and abuse-sensitive endpoints. The
# default LocMem cache is correct for the one-worker Procfile; multi-instance
# deployments must configure a shared atomic cache such as Redis.
RATE_LIMIT_ENABLED = env_bool("RATE_LIMIT_ENABLED", True)
RATE_LIMIT_TRUST_PROXY = env_bool("RATE_LIMIT_TRUST_PROXY", False)
RATE_LIMIT_GLOBAL_REQUESTS = int(os.getenv("RATE_LIMIT_GLOBAL_REQUESTS", "300"))
RATE_LIMIT_GLOBAL_WINDOW = int(os.getenv("RATE_LIMIT_GLOBAL_WINDOW", "60"))
RATE_LIMIT_LOGIN_REQUESTS = int(os.getenv("RATE_LIMIT_LOGIN_REQUESTS", "10"))
RATE_LIMIT_LOGIN_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "300"))
RATE_LIMIT_REGISTER_REQUESTS = int(os.getenv("RATE_LIMIT_REGISTER_REQUESTS", "5"))
RATE_LIMIT_REGISTER_WINDOW = int(os.getenv("RATE_LIMIT_REGISTER_WINDOW", "3600"))
RATE_LIMIT_CONTACT_REQUESTS = int(os.getenv("RATE_LIMIT_CONTACT_REQUESTS", "5"))
RATE_LIMIT_CONTACT_WINDOW = int(os.getenv("RATE_LIMIT_CONTACT_WINDOW", "3600"))
RATE_LIMIT_EMAIL_REQUESTS = int(os.getenv("RATE_LIMIT_EMAIL_REQUESTS", "5"))
RATE_LIMIT_EMAIL_WINDOW = int(os.getenv("RATE_LIMIT_EMAIL_WINDOW", "3600"))
RATE_LIMIT_AI_REQUESTS = int(os.getenv("RATE_LIMIT_AI_REQUESTS", "10"))
RATE_LIMIT_AI_WINDOW = int(os.getenv("RATE_LIMIT_AI_WINDOW", "3600"))

PRIVACY_CONSENT_VERSION = os.getenv("PRIVACY_CONSENT_VERSION", "2026-09-20")

# The detector service reads these values only when an analysis is requested.
# Keeping model identifiers and revisions in configuration makes detector
# upgrades independent from the staff view and the rest of the application.
AI_DETECTION_PRIMARY_MODEL = os.getenv(
    "AI_DETECTION_PRIMARY_MODEL",
    "ShantanuT01/vanguard-ai-text-detector",
)
AI_DETECTION_PRIMARY_REVISION = os.getenv(
    "AI_DETECTION_PRIMARY_REVISION",
    "823061be63b90f2b42f64ac1e1f82772e872533b",
)
AI_DETECTION_ENABLE_VALIDATION = env_bool(
    "AI_DETECTION_ENABLE_VALIDATION",
    False,
)
AI_DETECTION_VALIDATION_MODEL = os.getenv(
    "AI_DETECTION_VALIDATION_MODEL",
    "desklib/ai-text-detector-academic-v1.01",
)
AI_DETECTION_VALIDATION_REVISION = os.getenv(
    "AI_DETECTION_VALIDATION_REVISION",
    "main",
)

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
