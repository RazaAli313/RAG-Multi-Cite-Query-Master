import re

from django.core.exceptions import ValidationError


class PasswordValidator:
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, _user=None):
        if len(password) < self.min_length:
            raise ValidationError(f"The password must be at least {self.min_length} characters long.")

        if not any(char.islower() for char in password):
            raise ValidationError("The password must contain at least one lowercase character.")

        if not any(char.isupper() for char in password):
            raise ValidationError("The password must contain at least one uppercase character.")

        # Define a regular expression to match special characters
        special_characters_pattern = r"[!@#$%^&*()_+{}[\]:;<>,.?~]"
        if not re.search(special_characters_pattern, password):
            raise ValidationError("The password must contain at least one special character.")

    def get_help_text(self):
        return (
            f"The password must be at least {self.min_length} characters long and contain "
            "at least one lowercase character, one uppercase character, and one special character."
        )
