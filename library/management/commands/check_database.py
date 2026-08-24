"""Verify that Django can execute a query against its configured database."""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import DatabaseError


class Command(BaseCommand):
    help = "Check the configured PostgreSQL connection with a read-only query."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user")
                database_name, database_user = cursor.fetchone()
        except DatabaseError as exc:
            raise CommandError(
                "PostgreSQL connection failed. Check DATABASE_URL and whether "
                "the PostgreSQL service is running."
            ) from exc

        if connection.vendor != "postgresql":
            raise CommandError(
                f"Expected PostgreSQL, but Django is using {connection.vendor}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"PostgreSQL connection succeeded: database={database_name}, "
                f"user={database_user}."
            )
        )
