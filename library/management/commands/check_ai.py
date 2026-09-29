"""Show AI detector configuration and optionally run an end-to-end analysis."""

from time import monotonic

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library.services.ai_detection import (
    AIDetectionBenchmarkService,
    AIDetectionError,
    AIDetectionService,
)


class Command(BaseCommand):
    help = "Show AI detector configuration and optionally run a smoke analysis."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-analysis",
            action="store_true",
            help="Load the configured detector and analyze a safe sample.",
        )
        parser.add_argument(
            "--benchmark",
            action="store_true",
            help=(
                "Explicitly compare the primary Desklib model with Vanguard. "
                "The models are loaded sequentially."
            ),
        )

    def handle(self, *args, **options):
        self.stdout.write(f"AI detection engine: {settings.AI_DETECTION_ENGINE}")
        self.stdout.write(
            "Primary model: "
            f"{settings.AI_DETECTION_PRIMARY_MODEL} "
            f"@ {settings.AI_DETECTION_PRIMARY_REVISION}"
        )
        if settings.AI_DETECTION_ENGINE == "onnx":
            self.stdout.write(
                f"Local model directory: {settings.AI_DETECTION_MODEL_DIR}"
            )
            self.stdout.write("Runtime: ONNX Runtime CPU (PyTorch is not required)")
        elif settings.AI_DETECTION_ENGINE == "remote":
            self.stdout.write(
                f"Dedicated inference service: {settings.AI_DETECTION_REMOTE_URL}"
            )
            self.stdout.write("Remote model enforcement: strict (no fast fallback)")
        else:
            self.stdout.write(
                "Fast fallback enabled: "
                f"{'yes' if settings.AI_DETECTION_FALLBACK_TO_FAST else 'no'}"
            )
        if settings.AI_DETECTION_ENGINE == "transformer" or options["benchmark"]:
            self.stdout.write(
                "Benchmark model: "
                f"{settings.AI_DETECTION_COMPARISON_MODEL} "
                f"@ {settings.AI_DETECTION_COMPARISON_REVISION} "
                "(explicit benchmark only)"
            )
        if options["benchmark"] and not options["run_analysis"]:
            raise CommandError("--benchmark requires --run-analysis.")
        if options["benchmark"] and settings.AI_DETECTION_ENGINE != "transformer":
            raise CommandError(
                "--benchmark must run on the high-memory inference service with "
                "AI_DETECTION_ENGINE=transformer."
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
            service = (
                AIDetectionBenchmarkService(allow_model_download=True)
                if options["benchmark"]
                else AIDetectionService(allow_model_download=True)
            )
            result = service.analyze(sample)
        except AIDetectionError as exc:
            raise CommandError(f"AI analysis check failed: {exc}") from exc

        if settings.AI_DETECTION_ENGINE in {"onnx", "transformer"} and result.get(
            "fallback_used"
        ):
            raise CommandError(
                "AI analysis check failed: the configured model used the fast fallback."
            )
        if options["benchmark"] and not result.get("comparison_complete"):
            raise CommandError(
                "AI benchmark failed: Vanguard did not complete the comparison."
            )

        elapsed = monotonic() - started
        comparison = result.get("comparison")
        comparison_summary = (
            f"; {comparison['detector_name']} version {comparison['model_version']}"
            if comparison
            else ""
        )
        self.stdout.write(
            self.style.SUCCESS(
                "AI analysis check passed "
                f"({result['detector_name']} version {result['model_version']}"
                f"{comparison_summary}; {elapsed:.2f}s)."
            )
        )
