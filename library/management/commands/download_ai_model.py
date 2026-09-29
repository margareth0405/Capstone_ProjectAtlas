"""Download the pinned deployment-ready ONNX detector to the local project."""

from pathlib import Path
from shutil import copy2

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library.services.ai_detection import AIDetectionError, OnnxDistilBertDetector


class Command(BaseCommand):
    help = "Download and validate the pinned INT8 ONNX AI detector files."

    filenames = (
        "model_int8.onnx",
        "tokenizer.json",
        "tokenizer_config.json",
        "label_order.json",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=settings.AI_DETECTION_MODEL_DIR,
            help="Destination directory (defaults to AI_DETECTION_MODEL_DIR).",
        )

    def handle(self, *args, **options):
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as exc:
            raise CommandError(
                "huggingface_hub is unavailable. Install the project requirements."
            ) from exc

        output_dir = options["output_dir"].resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(
            "Downloading the pinned INT8 detector on this development computer..."
        )
        try:
            for filename in self.filenames:
                cached_path = hf_hub_download(
                    repo_id=settings.AI_DETECTION_PRIMARY_MODEL,
                    filename=filename,
                    revision=settings.AI_DETECTION_PRIMARY_REVISION,
                )
                copy2(cached_path, output_dir / filename)
        except Exception as exc:
            raise CommandError(f"AI model download failed: {exc}") from exc

        detector = OnnxDistilBertDetector(
            model_dir=output_dir,
            model_name=settings.AI_DETECTION_PRIMARY_MODEL,
            revision=settings.AI_DETECTION_PRIMARY_REVISION,
        )
        try:
            detector.prepare()
        except AIDetectionError as exc:
            raise CommandError(f"AI model validation failed: {exc}") from exc
        finally:
            detector.release()

        self.stdout.write(
            self.style.SUCCESS(
                f"Pinned INT8 detector downloaded and validated in {output_dir}."
            )
        )
