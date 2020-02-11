def build_json_api_identifier(type, id):
    return {
        'type': type,
        'id': id,
    }


def build_json_api_payload(type, data):
    return {
        'data': {
            'type': type,
            'attributes': data,
        },
    }
