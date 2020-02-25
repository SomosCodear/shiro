import os
import importlib

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
env_settings = importlib.import_module(f'shiro.settings.{ENVIRONMENT}')

globals().update(vars(env_settings))

try:
    # import local settings if present
    from .local import *  # noqa
except ImportError:
    pass
