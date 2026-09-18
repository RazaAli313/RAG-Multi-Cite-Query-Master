from dj_rest_auth.registration.serializers import (
    RegisterSerializer as DJRestAuthRegisterSerializer,
)
from dj_rest_auth.serializers import (
    UserDetailsSerializer as DJRestAuthUserDetailsSerializer,
)
from rest_framework import serializers


class RegisterSerializer(DJRestAuthRegisterSerializer):
    # Must override here: ACCOUNT_SIGNUP_FIELDS can't include "username" (no username field on User),
    # and dj-rest-auth treats any field missing from ACCOUNT_SIGNUP_FIELDS as required.
    username = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)

    def get_cleaned_data(self):
        return {
            "username": self.validated_data.get("username", ""),
            "password1": self.validated_data.get("password1", ""),
            "email": self.validated_data.get("email", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
        }


class UserDetailsSerializer(DJRestAuthUserDetailsSerializer):
    class Meta(DJRestAuthUserDetailsSerializer.Meta):
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
        )
