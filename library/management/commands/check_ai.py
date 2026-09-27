"""Show AI detector configuration and optionally run an end-to-end analysis."""

from time import monotonic

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library.services.ai_detection import AIDetectionError, AIDetectionService


class Command(BaseCommand):
    help = "Show AI detector configuration and optionally run a smoke analysis."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-analysis",
            action="store_true",
            help="Load the configured detector and analyze a safe sample.",
        )

    def handle(self, *args, **options):
        self.stdout.write(f"AI detection engine: {settings.AI_DETECTION_ENGINE}")
        self.stdout.write(f"Primary model: {settings.AI_DETECTION_PRIMARY_MODEL}")
        self.stdout.write(
            "Fast fallback enabled: "
            f"{'yes' if settings.AI_DETECTION_FALLBACK_TO_FAST else 'no'}"
        )
        if not options["run_analysis"]:
            self.stdout.write(
                self.style.WARNING(
                    "Configuration loaded. Add --run-analysis to load and test the detector."
                )
            )
            return

        sample = (
            "A careful research report begins with a focused question and explains "
            "how its evidence was selected. It compares competing interpretations, "
            "identifies limitations in the available sources, and distinguishes "
            "observations from conclusions. The final section describes what new "
            "evidence would strengthen or challenge the argument."
        )
        started = monotonic()
        try:
            result = AIDetectionService().analyze(sample)
        except AIDetectionError as exc:
            raise CommandError(f"AI analysis check failed: {exc}") from exc

        elapsed = monotonic() - started
        mode = "fallback" if result.get("fallback_used") else "primary"
        self.stdout.write(
            self.style.SUCCESS(
                "AI analysis check passed "
                f"({mode}; {result['detector_name']}; "
                f"version {result['model_version']}; {elapsed:.2f}s)."
            )
        )
