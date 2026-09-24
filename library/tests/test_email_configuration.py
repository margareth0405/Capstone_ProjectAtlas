"""Email setting and delivery-command regression coverage."""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings


class VerifyEmailCommandTests(SimpleTestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
    )
    def test_non_delivery_backend_is_rejected(self):
        with self.assertRaisesMessage(CommandError, "does not deliver messages"):
            call_command("verify_email", recipient="reader@example.com")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="ATLAS <atlas@example.com>",
    )
    @patch("library.management.commands.verify_email.EmailMessage")
    @patch("library.management.commands.verify_email.get_connection")
    def test_smtp_connection_and_message_are_used(self, get_connection, email_message):
        connection = MagicMock()
        get_connection.return_value = connection
        email_message.return_value.send.return_value = 1
        output = StringIO()

        call_command("verify_email", recipient="reader@example.com", stdout=output)

        connection.open.assert_called_once_with()
        connection.close.assert_called_once_with()
        email_message.assert_called_once_with(
            subject="[ATLAS] Email delivery check",
            body=(
                "ATLAS successfully connected to the configured email service "
                "and delivered this test message."
            ),
            from_email="ATLAS <atlas@example.com>",
            to=["reader@example.com"],
            connection=connection,
        )
        email_message.return_value.send.assert_called_once_with(fail_silently=False)
        self.assertIn("ATLAS test email sent", output.getvalue())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
    )
    def test_invalid_recipient_is_rejected_before_connecting(self):
        with self.assertRaisesMessage(CommandError, "valid email address"):
            call_command("verify_email", recipient="not-an-email")
