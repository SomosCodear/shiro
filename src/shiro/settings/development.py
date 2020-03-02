"""
Django develop settings for shiro project.
"""
from .base import *  # noqa: F403

# CORS
INSTALLED_APPS += [  # noqa: F405
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
] + MIDDLEWARE  # noqa: F405

CORS_ORIGIN_ALLOW_ALL = True

CACHES['afip'] = {  # noqa: F405
    'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
    'LOCATION': 'afip_cache_table',
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
