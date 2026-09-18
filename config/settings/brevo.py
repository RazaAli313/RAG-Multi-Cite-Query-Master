from decouple import config


EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

ANYMAIL = {
    "BREVO_API_KEY": config("BREVO_API_KEY"),
}
