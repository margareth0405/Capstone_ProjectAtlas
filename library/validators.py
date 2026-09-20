"""Password validators shared by registration, account creation, and recovery."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordCharacterValidator:
    """Require at least one number and one non-whitespace special character."""

    number_pattern = re.compile(r"\d")
    special_pattern = re.compile(r"[^\w\s]")

    def validate(self, password, user=None):
        errors = []
        if not self.number_pattern.search(password):
            errors.append(
                ValidationError(
                    _("Your password must contain at least one number."),
                    code="password_no_number",
                )
            )
        if not self.special_pattern.search(password):
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
            "Your password must contain at least one number and one special "
            "character, such as !, @, #, or $."
        )
