"""
Django develop settings for shiro project.
"""
import os
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
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_SES_REGION = os.getenv('AWS_SES_REGION', AWS_DEFAULT_REGION)
