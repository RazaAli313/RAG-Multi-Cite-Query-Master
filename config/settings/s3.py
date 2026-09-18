from decouple import config


AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN")
AWS_STATIC_LOCATION = config("AWS_STATIC_LOCATION", default="static")
AWS_MEDIA_LOCATION = config("AWS_MEDIA_LOCATION", default="media")
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

STORAGES = {  # noqa
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"location": AWS_MEDIA_LOCATION},
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"location": AWS_STATIC_LOCATION},
    },
}
