from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.generics import DestroyAPIView


class GoogleSocialLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class DeleteAccountAPIView(DestroyAPIView):
    def get_object(self):
        return self.request.user
