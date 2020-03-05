from django.conf import settings
from rest_framework_json_api import parsers, utils


class JSONParser(parsers.JSONParser):
    @staticmethod
    def parse_attributes(data):
        attributes = data.get('attributes')
        uses_format_translation = settings.JSON_API_FORMAT_FIELD_NAMES

        if not attributes:
            return dict()
        elif uses_format_translation:
            # convert back to python/rest_framework's preferred underscore format
            formatted_data = {}

            for key, value in utils.format_field_names(attributes, 'underscore').items():
                if isinstance(value, dict) and 'attributes' in value:
                    formatted_data[key] = {
                        'type': value['type'],
                        'attributes': JSONParser.parse_attributes(value),
                    }
                elif isinstance(value, list):
                    formatted_data[key] = [
                        {
                            'type': item['type'],
                            'attributes': JSONParser.parse_attributes(item),
                        } for item in value
                    ]
                else:
                    formatted_data[key] = value

            return formatted_data
        else:
            return attributes
