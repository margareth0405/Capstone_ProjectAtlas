"""Email delivery service for ATLAS contact submissions."""

from django.conf import settings
from django.core.mail import EmailMessage


class ContactDeliveryError(RuntimeError):
    """Raised when the configured email backend does not accept a message."""


class ContactEmailService:
    """Build and deliver contact email while preserving the visitor reply address."""

    email_message_class = EmailMessage

    def __init__(self, *, recipient=None, from_email=None):
        self.recipient = recipient or settings.SUPPORT_EMAIL
        self.from_email = from_email or settings.DEFAULT_FROM_EMAIL

    def deliver(self, contact_message, *, account_email):
        email = self.email_message_class(
            subject=f"[ATLAS Contact] {contact_message.subject}",
            body=self._build_body(contact_message, account_email=account_email),
            from_email=self.from_email,
            to=[self.recipient],
            reply_to=[contact_message.email],
        )
        if email.send(fail_silently=False) != 1:
            raise ContactDeliveryError(
                "The configured email backend did not accept the message."
            )
        return email

    @staticmethod
    def _build_body(contact_message, *, account_email):
        return chr(10).join(
            (
                f"Name: {contact_message.name}",
                f"Email: {contact_message.email}",
                f"ATLAS account: {account_email}",
                "",
                "Message:",
                contact_message.message,
            )
        )
