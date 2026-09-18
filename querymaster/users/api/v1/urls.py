from django.urls import include, path

from .views import DeleteAccountAPIView, GoogleSocialLoginView


urlpatterns = [
    path("registration/", include("dj_rest_auth.registration.urls")),
    path("registration/google/", GoogleSocialLoginView.as_view(), name="google_login"),
    path("delete-account/", DeleteAccountAPIView.as_view(), name="delete_account"),
    path("", include("dj_rest_auth.urls")),
]
