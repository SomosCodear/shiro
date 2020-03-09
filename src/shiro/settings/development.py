"""
Django develop settings for shiro project.
"""
from .base import *  # noqa: F403

CACHES['afip'] = {  # noqa: F405
    'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
    'LOCATION': 'afip_cache_table',
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
