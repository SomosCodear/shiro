from django.core import validators
from django.utils.translation import gettext_lazy as _


def validate_list(value):
    if not isinstance(value, list):
        raise validators.ValidationError(
            _('%(value)s is not a list'),
            params={'value': value},
        )


def validate_single_value(value):
    if isinstance(value, list) or isinstance(value, dict):
        raise validators.ValidationError(
            _('%(value)s is not a single value'),
            params={'value': value},
        )
