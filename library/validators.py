"""Password validators shared by registration, account creation, and recovery."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordCharacterValidator:
    """Require a number and any non-alphanumeric, non-space character."""

    @staticmethod
    def has_number(password):
        return any(character.isnumeric() for character in password)

    @staticmethod
    def has_special_character(password):
        # This intentionally accepts every Unicode punctuation or symbol
        # character, including underscores, currency signs, and emoji.
        return any(
            not character.isalnum() and not character.isspace()
            for character in password
        )

    def validate(self, password, user=None):
        errors = []
        if not self.has_number(password):
            errors.append(
                ValidationError(
                    _("Your password must contain at least one number."),
                    code="password_no_number",
                )
            )
        if not self.has_special_character(password):
            errors.append(
                ValidationError(
                    _("Your password must contain at least one special character."),
                    code="password_no_special_character",
                )
            )
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Your password must contain at least one number and one symbol or "
            "punctuation character. Any non-letter, non-number, non-space "
            "character is accepted."
        )
