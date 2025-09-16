# elearning/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add this if not present
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# Configuration des bases de données
if os.environ.get("USE_SQLITE", "false").lower() == "true":
    # Configuration SQLite pour les tests CI
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",  # Base de données en mémoire pour les tests
        }
    }
else:
    # Configuration PostgreSQL pour la production
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "elearning_db"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "password"),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

# ...

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "admin_dashboard",
    "users",
    "courses",
]

CRISPY_TEMPLATE_PACK = "bootstrap4"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "courses_dashboard"
LOGOUT_REDIRECT_URL = "login"

# Static files configuration
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Make sure you have this middleware configuration
MIDDLEWARE = [
    "middleware.URLDebugMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Update TEMPLATES setting
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ============================================
# ELASTICSEARCH CONFIGURATION
# ============================================
ELASTICSEARCH_ENABLED = (
    os.environ.get("ELASTICSEARCH_ENABLED", "false").lower() == "true"
)
ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST", "localhost:9200")
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "courses")
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY", "")

# ============================================
# SPARK PIPELINE CONFIGURATION
# ============================================
# Configuration Consumer (Learning Platform)
LEARNING_PLATFORM_URL = os.environ.get("LEARNING_PLATFORM_URL", "http://localhost:8000")

# ============================================
# REDIS CONFIGURATION (optionnel)
# ============================================
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Cache configuration avec Redis
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }

# ============================================
# EMAIL CONFIGURATION
# ============================================
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@elearning.com")

# ============================================
# NOTIFICATION CONFIGURATION
# ============================================
EMAIL_NOTIFICATIONS_ENABLED = (
    os.environ.get("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() == "true"
)
ADMIN_NOTIFICATION_EMAILS = [
    email.strip()
    for email in os.environ.get("ADMIN_NOTIFICATION_EMAILS", "").split(",")
    if email.strip()
]

# Webhooks configuration
NOTIFICATION_WEBHOOKS = {}
if os.environ.get("SLACK_WEBHOOK_URL"):
    NOTIFICATION_WEBHOOKS["slack"] = os.environ.get("SLACK_WEBHOOK_URL")
if os.environ.get("DISCORD_WEBHOOK_URL"):
    NOTIFICATION_WEBHOOKS["discord"] = os.environ.get("DISCORD_WEBHOOK_URL")
if os.environ.get("TEAMS_WEBHOOK_URL"):
    NOTIFICATION_WEBHOOKS["teams"] = os.environ.get("TEAMS_WEBHOOK_URL")

# ============================================
# FILE UPLOAD CONFIGURATION
# ============================================
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", "52428800"))  # 50MB par défaut
ALLOWED_UPLOAD_EXTENSIONS = os.environ.get(
    "ALLOWED_UPLOAD_EXTENSIONS", "csv,json,xlsx"
).split(",")

# Django file upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# Development settings
if DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
    ]

    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ] + MIDDLEWARE

    INTERNAL_IPS = [
        "127.0.0.1",
    ]

    # Configuration pour le hot reload
    WATCHMAN_RELOAD = True
    WATCHMAN_RELOAD_INTERVAL = 1

# ============================================
# LOGGING CONFIGURATION
# ============================================
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DJANGO_LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "django.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "services": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "admin_dashboard": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

# Ajoutez ces lignes pour plus de détails en mode DEBUG
if DEBUG:
    LOGGING["loggers"]["django.db.backends"] = {
        "handlers": ["console"],
        "level": "DEBUG",
    }

# ============================================
# SECURITY SETTINGS
# ============================================
# Security settings (à activer en production)
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() == "true"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "False").lower() == "true"
SECURE_CONTENT_TYPE_NOSNIFF = (
    os.environ.get("SECURE_CONTENT_TYPE_NOSNIFF", "True").lower() == "true"
)
SECURE_BROWSER_XSS_FILTER = (
    os.environ.get("SECURE_BROWSER_XSS_FILTER", "True").lower() == "true"
)
SESSION_COOKIE_SECURE = (
    os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
)
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"

# Add this after the BASE_DIR setting
ROOT_URLCONF = "elearning.urls"
