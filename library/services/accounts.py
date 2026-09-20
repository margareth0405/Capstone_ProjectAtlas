"""Account identity policies shared by registration and sign-in forms."""

from django.conf import settings


class AccountEmailPolicy:
    """Validate role-specific institutional email requirements."""

    teacher_role = "teacher"
    teacher_error = "Teacher accounts must use an official @deped.gov.ph email address."

    def __init__(self, teacher_domains=None):
        configured = (
            getattr(settings, "TEACHER_EMAIL_DOMAINS", ("deped.gov.ph",))
            if teacher_domains is None
            else teacher_domains
        )
        self.teacher_domains = tuple(
            domain.strip().lower().lstrip("@")
            for domain in configured
            if domain.strip()
        )

    def error_for(self, *, email, role):
        if role != self.teacher_role:
            return ""
        domain = email.strip().lower().rpartition("@")[2]
        if any(
            domain == allowed or domain.endswith(f".{allowed}")
            for allowed in self.teacher_domains
        ):
            return ""
        return self.teacher_error
