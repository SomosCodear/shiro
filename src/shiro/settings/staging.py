"""
Django develop settings for shiro project.
"""
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F403

# Cache
CACHES['afip'] = {  # noqa: F405
    'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
    'LOCATION': 'afip_cache_table',
}

# Email
EMAIL_BACKEND = 'django_amazon_ses.EmailBackend'

# Files Storage
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# AWS
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_SES_REGION = os.getenv('AWS_SES_REGION', AWS_DEFAULT_REGION)

# Sentry
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    send_default_pii=True,
)
