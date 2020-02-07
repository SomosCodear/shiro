def build_json_api_payload(type, data):
    return {
        'data': {
            'type': type,
            'attributes': data,
        },
    }
