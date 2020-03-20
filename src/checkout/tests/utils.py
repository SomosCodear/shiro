from ..utils import quantize_decimal  # noqa: F401
from .. import authentication


def build_json_api_identifier(type, id):
    return {
        'type': type,
        'id': id,
    }


def build_json_api_resource(type, data):
    return {
        'type': type,
        'attributes': data,
    }


def build_json_api_payload(type, data):
    return {
        'data': build_json_api_resource(type, data),
    }


def build_authentication_credentials(schema, *args):
    return {
        'HTTP_AUTHORIZATION': ' '.join([schema, *args]),
    }


def build_customer_authentication_credentials(customer):
    return build_authentication_credentials(
        authentication.CUSTOMER_AUTH_SCHEMA,
        customer.user.email,
        customer.identity_document,
    )
