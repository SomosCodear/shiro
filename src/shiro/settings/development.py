"""
Django develop settings for shiro project.
"""
from .base import *  # noqa

CACHES['afip'] = {  # noqa
    'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
    'LOCATION': 'afip_cache_table',
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
