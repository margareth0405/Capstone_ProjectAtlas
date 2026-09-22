"""Check the configured media backend and optionally perform a safe round trip."""

from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Show the media backend and optionally test write/read/delete access."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-test",
            action="store_true",
            help="Create, read, and delete one temporary storage probe.",
        )

    def handle(self, *args, **options):
        backend = settings.STORAGES["default"]["BACKEND"]
        self.stdout.write(f"Media storage backend: {backend}")
        if not options["write_test"]:
            self.stdout.write(
                self.style.WARNING(
                    "Configuration loaded. Add --write-test to verify remote access."
                )
            )
            return

        probe_name = f"_atlas_storage_checks/{uuid4().hex}.txt"
        saved_name = ""
        try:
            saved_name = default_storage.save(
                probe_name,
                ContentFile(b"ATLAS storage connectivity check"),
            )
            with default_storage.open(saved_name, "rb") as probe:
                if probe.read() != b"ATLAS storage connectivity check":
                    raise CommandError("Storage returned unexpected probe content.")
        except Exception as exc:
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Storage round-trip failed: {exc}") from exc
        finally:
            if saved_name:
                try:
                    default_storage.delete(saved_name)
                except Exception as exc:
                    raise CommandError(
                        f"Storage worked, but the temporary probe could not be deleted: {exc}"
                    ) from exc

        self.stdout.write(self.style.SUCCESS("Storage write/read/delete check passed."))
