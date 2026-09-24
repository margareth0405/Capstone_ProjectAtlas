"""Verify the configured outbound email transport with one test message."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from library.services.deployment import DeploymentReadinessService


class Command(BaseCommand):
    help = "Connect to the configured email backend and optionally send a test message."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            dest="recipient",
            help="Mailbox that should receive an ATLAS test message.",
        )

    def handle(self, *args, **options):
        del args
        recipient = (options.get("recipient") or "").strip()
        if recipient:
            try:
                validate_email(recipient)
            except ValidationError as exc:
                raise CommandError("--to must be a valid email address.") from exc

        if settings.EMAIL_BACKEND in DeploymentReadinessService.development_email_backends:
            raise CommandError(
                "The configured email backend does not deliver messages. Set "
                "DJANGO_EMAIL_BACKEND to django.core.mail.backends.smtp.EmailBackend."
            )

        connection = get_connection(fail_silently=False)
        try:
            connection.open()
            if recipient:
                message = EmailMessage(
                    subject="[ATLAS] Email delivery check",
                    body=(
                        "ATLAS successfully connected to the configured email service "
                        "and delivered this test message."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient],
                    connection=connection,
                )
                if message.send(fail_silently=False) != 1:
                    raise CommandError("The email backend did not accept the test message.")
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"Email verification failed: {exc}") from exc
        finally:
            connection.close()

        if recipient:
            self.stdout.write(
                self.style.SUCCESS(f"ATLAS test email sent to {recipient}.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("ATLAS connected to the configured email service.")
            )
