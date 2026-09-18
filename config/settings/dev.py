from .base import *  # noqa


DEBUG = True
ENABLE_DEBUG_TOOLBAR = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS += [  # noqa
        "debug_toolbar",
        "silk",
    ]

    MIDDLEWARE += [  # noqa
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "silk.middleware.SilkyMiddleware",
    ]

    INTERNAL_IPS = [
        "127.0.0.1",
    ]

    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: ENABLE_DEBUG_TOOLBAR}
