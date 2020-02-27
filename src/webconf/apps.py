from django.apps import AppConfig


class WebconfConfig(AppConfig):
    name = 'webconf'

    def ready(self):
        from . import signals  # noqa: F401
        print(signals)
