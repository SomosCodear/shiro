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

        if len(auth_parts) == 3 and auth_parts[0] == CUSTOMER_AUTH_SCHEMA:
            email, identity_document = auth_parts[1:]

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
