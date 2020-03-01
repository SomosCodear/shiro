from django.apps import AppConfig
from django.conf import settings


class WebconfConfig(AppConfig):
    name = 'webconf'

    def ready(self):
        if not settings.TESTING:
            from . import signals  # noqa: F401
