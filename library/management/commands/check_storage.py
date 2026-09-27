"""Check the configured media backend and optionally perform a safe round trip."""

from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from library.models import LibraryItem


class Command(BaseCommand):
    help = "Show the media backend and optionally test write/read/delete access."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-test",
            action="store_true",
            help="Create, read, and delete one temporary storage probe.",
        )
        parser.add_argument(
            "--check-references",
            action="store_true",
            help="Verify that every repository file referenced by the database exists.",
        )

    def handle(self, *args, **options):
        backend = settings.STORAGES["default"]["BACKEND"]
        self.stdout.write(f"Media storage backend: {backend}")
        if not options["write_test"] and not options["check_references"]:
            self.stdout.write(
                self.style.WARNING(
                    "Configuration loaded. Add --write-test to verify remote access."
                )
            )
            return

        if options["write_test"]:
            self._run_write_test()
        if options["check_references"]:
            self._check_references()

    def _run_write_test(self):
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

    def _check_references(self):
        missing = []
        for item in LibraryItem.objects.iterator():
            for field_name in ("cover_image", "resource_abstract", "resource"):
                field_file = getattr(item, field_name)
                if field_file.name and not field_file.storage.exists(field_file.name):
                    missing.append(f"item {item.pk} {field_name}: {field_file.name}")

        if missing:
            details = "\n".join(f"- {entry}" for entry in missing[:20])
            remainder = len(missing) - 20
            if remainder > 0:
                details += f"\n- ...and {remainder} more"
            raise CommandError(
                f"Found {len(missing)} missing repository object(s):\n{details}"
            )

        self.stdout.write(
            self.style.SUCCESS("All repository database file references exist.")
        )
