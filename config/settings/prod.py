from .base import *  # noqa
from .brevo import *  # noqa
from .s3 import *  # noqa
from .sentry import *  # noqa


DEBUG = False
ENABLE_DEBUG_TOOLBAR = False

INSTALLED_APPS += [  # noqa
    "anymail",
    "storages",
    "health_check.storage",
    "health_check.contrib.s3boto3_storage",
]

STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_STATIC_LOCATION}/"  # noqa
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_MEDIA_LOCATION}/"  # noqa
