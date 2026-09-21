"""Verify the database, migrations, and production configuration."""

from django.core import checks
from django.core.management.base import BaseCommand, CommandError

from library.services.deployment import (
    DeploymentReadinessService,
    HealthCheckService,
)


class Command(BaseCommand):
    help = "Verify ATLAS production settings, database health, and migrations."

    def handle(self, *args, **options):
        check_messages = checks.run_checks(include_deployment_checks=True)
        errors = [
            message
            for message in check_messages
            if message.is_serious()
            or (
                message.id.startswith("security.")
                and message.id != "security.W021"
            )
        ]
        for message in check_messages:
            self.stdout.write(str(message))
        if errors:
            raise CommandError(
                f"Deployment verification found {len(errors)} blocking issue(s)."
            )

        health, healthy = HealthCheckService().check()
        if not healthy:
            raise CommandError("The configured PostgreSQL database is unavailable.")

        try:
            pending = DeploymentReadinessService().pending_migrations()
        except Exception as exc:
            raise CommandError(
                "ATLAS could not inspect the configured database migrations."
            ) from exc
        if pending:
            raise CommandError(
                "Unapplied migrations: " + ", ".join(pending)
            )

        self.stdout.write(
            self.style.SUCCESS(
                "ATLAS deployment verification passed: settings, PostgreSQL, "
                "and migrations are ready."
            )
        )
