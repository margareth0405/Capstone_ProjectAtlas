"""Unit tests for the replaceable local AI Detection service."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from library.services.ai_detection import (
    AIDetectionError,
    AIDetectionService,
    VanguardDetector,
)


class FakePipeline:
    def __init__(self, predictions, commit_hash="detector-commit-123"):
        self.predictions = predictions
        self.model = SimpleNamespace(
            config=SimpleNamespace(_commit_hash=commit_hash)
        )

    def __call__(self, chunks, **kwargs):
        return self.predictions


class VanguardDetectorTests(SimpleTestCase):
    def tearDown(self):
        VanguardDetector._pipeline = None

    def test_long_text_is_chunked_and_probabilities_are_averaged(self):
        pipeline = FakePipeline(
            [
                {"label": "LABEL_0", "score": 0.80},
                {"label": "LABEL_0", "score": 0.30},
            ]
        )
        detector = VanguardDetector()

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("word " * 300)

        self.assertEqual(result["chunks_analyzed"], 2)
        self.assertEqual(result["ai_probability"], 55.0)
        self.assertEqual(result["human_probability"], 45.0)
        self.assertEqual(result["label"], "Mixed / uncertain")
        self.assertEqual(result["detector_name"], "Vanguard")
        self.assertEqual(result["model_version"], "detector-commit-123")

    def test_low_ai_probability_reports_high_human_probability(self):
        detector = VanguardDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 0.08}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("Evidence based writing " * 40)

        self.assertEqual(result["ai_probability"], 8.0)
        self.assertEqual(result["human_probability"], 92.0)
        self.assertEqual(result["label"], "Low AI likelihood")

    def test_unknown_model_label_raises_safe_error(self):
        detector = VanguardDetector()
        pipeline = FakePipeline([{"label": "unexpected", "score": 0.9}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            with self.assertRaisesMessage(
                AIDetectionError,
                "unknown classification",
            ):
                detector.analyze("A sufficiently long sample " * 30)


@override_settings(AI_DETECTION_ENABLE_VALIDATION=False)
class AIDetectionServiceTests(SimpleTestCase):
    class StubDetector:
        def __init__(self, name, probability):
            self.name = name
            self.probability = probability

        def analyze(self, text):
            return {
                "detector_name": self.name,
                "ai_probability": self.probability,
            }

    def test_primary_detector_is_hidden_behind_service(self):
        primary = self.StubDetector("Primary", 61.0)

        result = AIDetectionService(primary_detector=primary).analyze("sample")

        self.assertEqual(result["detector_name"], "Primary")
        self.assertNotIn("validation", result)

    def test_optional_validator_uses_the_same_interface(self):
        primary = self.StubDetector("Primary", 61.0)
        validator = self.StubDetector("Academic validator", 58.0)

        result = AIDetectionService(
            primary_detector=primary,
            validation_detector=validator,
        ).analyze("sample")

        self.assertEqual(result["validation"]["detector_name"], "Academic validator")
