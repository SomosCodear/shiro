from rest_framework import authentication, exceptions
from . import models

__all__ = ['CustomerAuthentication', 'CUSTOMER_AUTH_SCHEMA']


CUSTOMER_AUTH_SCHEMA = 'Customer'


class CustomerAuthentication(authentication.BaseAuthentication):
    def _get_authentication_parameters(self, request):
        email = None
        identity_document = None
        auth_header = authentication.get_authorization_header(request)
        auth_parts = str(auth_header, 'utf-8').split(' ') if auth_header else []
        auth_schema = auth_parts.pop(0) if len(auth_parts) > 0 else None

        if auth_schema == CUSTOMER_AUTH_SCHEMA:
            if len(auth_parts) == 2:
                email, identity_document = auth_parts
            elif len(auth_parts) == 1:
                token = auth_parts[0]
                email, identity_document = models.Customer.parse_customer_token(token)

        return email, identity_document

    def authenticate(self, request):
        email, identity_document = self._get_authentication_parameters(request)

        if email and identity_document:
            try:
                customer = models.Customer.objects.get(
                    user__email__iexact=email,
                    identity_document__iexact=identity_document,
                )
            except models.Customer.DoesNotExist:
                raise exceptions.AuthenticationFailed()

            return customer.user, CUSTOMER_AUTH_SCHEMA
