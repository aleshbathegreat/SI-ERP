from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only")
if not DEBUG and SECRET_KEY.startswith("django-insecure"):
    raise RuntimeError("DJANGO_SECRET_KEY must be set for production (DEBUG=False)")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]
# SaaS custom domains / *.root — Host still validated in TenantHostMiddleware
PLATFORM_ROOT_DOMAIN = os.getenv("PLATFORM_ROOT_DOMAIN", "").strip().lower()
PLATFORM_HOSTS = os.getenv("PLATFORM_HOSTS", "").strip()
if PLATFORM_ROOT_DOMAIN:
    ALLOWED_HOSTS.append(PLATFORM_ROOT_DOMAIN)
    ALLOWED_HOSTS.append(f".{PLATFORM_ROOT_DOMAIN}")  # all tenant subdomains
if os.getenv("ALLOW_TENANT_CUSTOM_DOMAINS", "true").lower() in ("1", "true", "yes"):
    if "*" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append("*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "core",
    "accounts",
    "finance",
    "hr",
    "payroll",
    "ops",
    "crm",
    "dms",
    "projects",
    "mfg",
    "contracts",
    "service",
    "qms",
    "ess",
    "integrations",
    "notifications",
    "comments",
    "tasks",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.jwt_middleware.JWTAuthenticationMiddleware",
    "core.host_middleware.TenantHostMiddleware",
    "core.middleware.SubscriptionGateMiddleware",
    "core.audit_middleware.MutationAuditMiddleware",
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

# SQLite for demo; set DATABASE_URL / Postgres env for production
_db_engine = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")
if _db_engine.endswith("postgresql"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "sigbl_erp"),
            "USER": os.getenv("DB_USER", "sigbl"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("DB_NAME", "db.sqlite3"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_ROOT = BASE_DIR / "backups"

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Absolute base for /media/ (API public URL). Used when request is unavailable.
PUBLIC_MEDIA_BASE = os.getenv("PUBLIC_MEDIA_BASE", "").rstrip("/")
MEDIA_URL = os.getenv("DJANGO_MEDIA_URL", "/media/")

# Allow browser calls from tenant custom domains / subdomains
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://localhost:\d+$",
    r"^https?://127\.0\.0\.1:\d+$",
]
if PLATFORM_ROOT_DOMAIN:
    root_re = PLATFORM_ROOT_DOMAIN.replace(".", r"\.")
    CORS_ALLOWED_ORIGIN_REGEXES.append(rf"^https?://([\w-]+\.)?{root_re}(:\d+)?$")


def _cors_allow_tenant_origin(sender, request, **kwargs):
    """Dynamically allow Origin when it matches a known tenant custom domain."""
    origin = request.headers.get("Origin") or ""
    if not origin:
        return False
    from urllib.parse import urlparse

    from core.tenancy import host_allowed

    host = urlparse(origin).hostname
    return bool(host and host_allowed(host))


try:
    from corsheaders.signals import check_request_enabled

    check_request_enabled.connect(_cors_allow_tenant_origin)
except Exception:
    pass

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "accounts.permissions.HasOpenSubscription",
        "accounts.permissions.HasModulePermission",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "30/min"),
        "user": os.getenv("THROTTLE_USER", "120/min"),
        "login": os.getenv("THROTTLE_LOGIN", "30/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    # Absolute session: one refresh token issued at login, dead after 24 hours.
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=int(os.getenv("JWT_REFRESH_HOURS", "24"))),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SIGBL ERP Cloud API",
    "DESCRIPTION": "SIGBL ERP Cloud — Finance · HR · Payroll SaaS API",
    "VERSION": "1.1.0",
}

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@sigbl.local")

# Production HTTPS / cookie hardening
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("1", "true", "yes")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MFA_ISSUER = os.getenv("MFA_ISSUER", "SIGBL ERP")

# FBR / PRAL e-invoice: leave FBR_API_URL empty for honest sandbox mode (no transmission)
FBR_API_URL = os.getenv("FBR_API_URL", "").strip()
FBR_API_TOKEN = os.getenv("FBR_API_TOKEN", "").strip()
FBR_TIMEOUT = int(os.getenv("FBR_TIMEOUT", "20"))
SOD_ENFORCE = os.getenv("SOD_ENFORCE", "True").lower() in ("1", "true", "yes")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "logs" / "erp.log"),
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "core": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
    },
}

# Ensure log/backup dirs exist
(BASE_DIR / "logs").mkdir(exist_ok=True)
BACKUP_ROOT.mkdir(exist_ok=True)
