import decimal


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


def quantize_decimal(value):
    return value.quantize(decimal.Decimal('0.01'))
