from allauth.account.adapter import (
    DefaultAccountAdapter as AllAuthDefaultAccountAdapter,
)
from django.contrib.sites.shortcuts import get_current_site
from django.utils.crypto import get_random_string


class DefaultAccountAdapter(AllAuthDefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        current_site = get_current_site(request)
        ctx = {
            "user": emailconfirmation.email_address.user,
            "current_site": current_site,
            "key": emailconfirmation.key,
        }
        if signup:
            email_template = "account/email/email_confirmation_signup_otp"
        else:
            email_template = "account/email/email_confirmation_otp"
        self.send_mail(email_template, emailconfirmation.email_address.email, ctx)

    def generate_emailconfirmation_key(self, _email):
        key = get_random_string(4).lower()
        return key
