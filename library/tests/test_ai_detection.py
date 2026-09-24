"""Unit tests for the replaceable local AI Detection service."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from library.services.ai_detection import (
    AcademicBertDetector,
    AIDetectionError,
    AIDetectionService,
    FastWritingPatternDetector,
)
from library.services.documents import DocumentTextExtractor


class FakePipeline:
    def __init__(self, predictions, commit_hash="detector-commit-123"):
        self.predictions = predictions
        self.model = SimpleNamespace(
            config=SimpleNamespace(_commit_hash=commit_hash)
        )

    def __call__(self, chunks, **kwargs):
        return self.predictions


class AcademicBertDetectorTests(SimpleTestCase):
    def tearDown(self):
        AcademicBertDetector._pipeline = None

    def test_long_text_is_chunked_and_probabilities_are_averaged(self):
        pipeline = FakePipeline(
            [
                {"label": "LABEL_1", "score": 0.80},
                {"label": "LABEL_0", "score": 0.70},
            ]
        )
        detector = AcademicBertDetector()

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("word " * 300)

        self.assertEqual(result["chunks_analyzed"], 2)
        self.assertEqual(result["ai_probability"], 55.0)
        self.assertEqual(result["human_probability"], 45.0)
        self.assertEqual(result["label"], "Mixed / uncertain")
        self.assertEqual(result["detector_name"], "Academic BERT")
        self.assertEqual(result["model_version"], "detector-commit-123")

    def test_low_ai_probability_reports_high_human_probability(self):
        detector = AcademicBertDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 0.92}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("Evidence based writing " * 40)

        self.assertEqual(result["ai_probability"], 8.0)
        self.assertEqual(result["human_probability"], 92.0)
        self.assertEqual(result["label"], "Low AI-pattern score")

    def test_unknown_model_label_raises_safe_error(self):
        detector = AcademicBertDetector()
        pipeline = FakePipeline([{"label": "unexpected", "score": 0.9}])

        with (
            patch.object(detector, "_get_pipeline", return_value=pipeline),
            self.assertRaisesMessage(
                AIDetectionError,
                "unknown classification",
            ),
        ):
            detector.analyze("A sufficiently long sample " * 30)


class FastWritingPatternDetectorTests(SimpleTestCase):
    def test_fast_detector_returns_complete_bounded_result(self):
        detector = FastWritingPatternDetector()
        text = (
            "Research begins with a focused question. Students compare sources, "
            "record conflicting evidence, and explain why one interpretation is "
            "more convincing than another. A careful conclusion also identifies "
            "the study's limits and suggests what should be examined next. "
        ) * 3

        result = detector.analyze(text)

        self.assertGreaterEqual(result["ai_probability"], 0)
        self.assertLessEqual(result["ai_probability"], 100)
        self.assertAlmostEqual(
            result["ai_probability"] + result["human_probability"],
            100,
        )
        self.assertEqual(result["detector_name"], "ATLAS Fast Pattern Review")
        self.assertEqual(result["model_version"], "1.0")
        self.assertIn(result["tone"], {"low", "mixed", "high"})


class DocumentTextExtractorTests(SimpleTestCase):
    def test_pdf_extraction_stops_after_analysis_character_limit(self):
        pages = [SimpleNamespace(extract_text=lambda: "A" * 60) for _ in range(10)]
        reader = SimpleNamespace(is_encrypted=False, pages=pages)

        with patch("pypdf.PdfReader", return_value=reader):
            text = DocumentTextExtractor._extract_pdf(
                BytesIO(b"%PDF-test"),
                character_limit=100,
                page_limit=75,
            )

        self.assertEqual(len(text), 121)


@override_settings(
    AI_DETECTION_ENGINE="fast",
    AI_DETECTION_ENABLE_VALIDATION=False,
)
class AIDetectionServiceTests(SimpleTestCase):
    class StubDetector:
        def __init__(self, name, probability):
            self.name = name
            self.probability = probability

        def analyze(self, text):
            classification, tone = (
                ("High AI-pattern score", "high")
                if self.probability >= 70
                else ("Low AI-pattern score", "low")
            )
            return {
                "detector_name": self.name,
                "ai_probability": self.probability,
                "label": classification,
                "tone": tone,
            }

    def test_primary_detector_is_hidden_behind_service(self):
        primary = self.StubDetector("Primary", 61.0)

        result = AIDetectionService(primary_detector=primary).analyze("sample")

        self.assertEqual(result["detector_name"], "Primary")
        self.assertNotIn("validation", result)

    def test_fast_engine_does_not_construct_transformer_detector(self):
        with patch.object(
            AIDetectionService.primary_detector_class,
            "__init__",
            side_effect=AssertionError("transformer should not load"),
        ):
            result = AIDetectionService().analyze("Evidence and reasoning. " * 20)

        self.assertEqual(result["detector_name"], "ATLAS Fast Pattern Review")

    def test_optional_validator_uses_the_same_interface(self):
        primary = self.StubDetector("Primary", 61.0)
        validator = self.StubDetector("Academic validator", 58.0)

        result = AIDetectionService(
            primary_detector=primary,
            validation_detector=validator,
        ).analyze("sample")

        self.assertEqual(result["validation"]["detector_name"], "Academic validator")
        self.assertTrue(result["validation"]["agrees_with_primary"])
        self.assertFalse(result["detectors_disagree"])

    def test_disagreeing_detectors_return_uncertain_result(self):
        primary = self.StubDetector("Primary", 72.0)
        validator = self.StubDetector("Academic validator", 31.0)

        result = AIDetectionService(
            primary_detector=primary,
            validation_detector=validator,
        ).analyze("sample")

        self.assertEqual(result["label"], "Uncertain — detectors disagree")
        self.assertEqual(result["tone"], "mixed")
        self.assertTrue(result["detectors_disagree"])
        self.assertFalse(result["validation"]["agrees_with_primary"])
