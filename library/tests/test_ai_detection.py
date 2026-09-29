"""Unit tests for the replaceable local AI Detection service."""

from io import BytesIO, StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from library.services.ai_detection import (
    AIDetectionError,
    AIDetectionService,
    FastWritingPatternDetector,
    GradientAIDetector,
    VanguardAIDetector,
)
from library.services.documents import DocumentTextExtractor


class FakePipeline:
    def __init__(self, predictions, commit_hash="detector-commit-123"):
        self.predictions = predictions
        self.call_kwargs = None
        self.model = SimpleNamespace(
            config=SimpleNamespace(_commit_hash=commit_hash)
        )

    def __call__(self, chunks, **kwargs):
        self.call_kwargs = kwargs
        return self.predictions


class GradientAIDetectorTests(SimpleTestCase):
    def tearDown(self):
        GradientAIDetector._pipeline = None

    def test_long_text_is_chunked_and_probabilities_are_averaged(self):
        pipeline = FakePipeline(
            [
                {"label": "LABEL_0", "score": 0.80},
                {"label": "LABEL_0", "score": 0.30},
            ]
        )
        detector = GradientAIDetector()

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("word " * 300)

        self.assertEqual(result["chunks_analyzed"], 2)
        self.assertEqual(result["ai_probability"], 55.0)
        self.assertEqual(result["human_probability"], 45.0)
        self.assertEqual(result["label"], "Mixed / uncertain")
        self.assertEqual(result["detector_name"], "Gradient AI Text Detector")
        self.assertEqual(
            result["model_name"],
            "ShantanuT01/gradient-ai-text-detector",
        )
        self.assertEqual(result["model_version"], "detector-commit-123")
        self.assertEqual(pipeline.call_kwargs["function_to_apply"], "sigmoid")

    def test_low_ai_probability_reports_high_human_probability(self):
        detector = GradientAIDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 0.08}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("Evidence based writing " * 40)

        self.assertEqual(result["ai_probability"], 8.0)
        self.assertEqual(result["human_probability"], 92.0)
        self.assertEqual(result["label"], "Low AI-pattern score")

    def test_single_output_is_used_as_ai_probability_regardless_of_label_name(self):
        detector = GradientAIDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 0.92}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("A sufficiently long sample " * 30)

        self.assertEqual(result["ai_probability"], 92.0)
        self.assertEqual(result["human_probability"], 8.0)

    def test_out_of_range_probability_raises_safe_error(self):
        detector = GradientAIDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 1.1}])

        with (
            patch.object(detector, "_get_pipeline", return_value=pipeline),
            self.assertRaisesMessage(
                AIDetectionError,
                "confidence outside the expected range",
            ),
        ):
            detector.analyze("A sufficiently long sample " * 30)


class VanguardAIDetectorTests(SimpleTestCase):
    def tearDown(self):
        VanguardAIDetector._pipeline = None

    def test_vanguard_uses_single_sigmoid_output_as_ai_probability(self):
        detector = VanguardAIDetector()
        pipeline = FakePipeline(
            [{"label": "LABEL_0", "score": 0.73}],
            commit_hash="vanguard-commit-456",
        )

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("Evidence based writing " * 40)

        self.assertEqual(result["ai_probability"], 73.0)
        self.assertEqual(result["human_probability"], 27.0)
        self.assertEqual(result["detector_name"], "Vanguard AI Text Detector")
        self.assertEqual(
            result["model_name"],
            "ShantanuT01/vanguard-ai-text-detector",
        )
        self.assertEqual(result["model_version"], "vanguard-commit-456")
        self.assertEqual(pipeline.call_kwargs["function_to_apply"], "sigmoid")


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


@override_settings(AI_DETECTION_ENGINE="fast")
class AIDetectionServiceTests(SimpleTestCase):
    class StubDetector:
        def __init__(self, name, probability):
            self.name = name
            self.probability = probability

        def analyze(self, text):
            if self.probability >= 70:
                classification, tone = "High AI-pattern score", "high"
            elif self.probability >= 40:
                classification, tone = "Mixed / uncertain", "mixed"
            else:
                classification, tone = "Low AI-pattern score", "low"
            return {
                "score": self.probability,
                "detector_name": self.name,
                "ai_probability": self.probability,
                "human_probability": 100 - self.probability,
                "confidence": max(self.probability, 100 - self.probability),
                "chunks_analyzed": 1,
                "model_name": f"test/{self.name.lower()}",
                "model_version": "test-revision",
                "label": classification,
                "tone": tone,
            }

    class FailingDetector:
        def analyze(self, text):
            raise AIDetectionError("model unavailable")

    def test_primary_detector_is_hidden_behind_service(self):
        primary = self.StubDetector("Primary", 61.0)

        result = AIDetectionService(primary_detector=primary).analyze("sample")

        self.assertEqual(result["detector_name"], "Primary")

    def test_gradient_and_vanguard_results_are_reported_separately(self):
        result = AIDetectionService(
            primary_detector=self.StubDetector("Gradient", 61.0),
            comparison_detector=self.StubDetector("Vanguard", 58.0),
        ).analyze("sample")

        self.assertEqual(result["primary"]["detector_name"], "Gradient")
        self.assertEqual(result["primary"]["ai_probability"], 61.0)
        self.assertEqual(result["comparison"]["detector_name"], "Vanguard")
        self.assertEqual(result["comparison"]["ai_probability"], 58.0)
        self.assertTrue(result["comparison_complete"])
        self.assertFalse(result["detectors_disagree"])
        self.assertEqual(result["score_difference"], 3.0)

    def test_disagreement_is_marked_inconclusive(self):
        result = AIDetectionService(
            primary_detector=self.StubDetector("Gradient", 72.0),
            comparison_detector=self.StubDetector("Vanguard", 31.0),
        ).analyze("sample")

        self.assertEqual(result["label"], "Inconclusive — models disagree")
        self.assertEqual(result["tone"], "mixed")
        self.assertTrue(result["detectors_disagree"])
        self.assertEqual(result["score_difference"], 41.0)

    def test_comparison_failure_is_reported_without_discarding_gradient(self):
        result = AIDetectionService(
            primary_detector=self.StubDetector("Gradient", 72.0),
            comparison_detector=self.FailingDetector(),
        ).analyze("sample")

        self.assertEqual(result["detector_name"], "Gradient")
        self.assertFalse(result["comparison_complete"])
        self.assertIn("Vanguard could not complete", result["comparison_error"])
        self.assertNotIn("comparison", result)

    def test_fast_engine_does_not_construct_transformer_detector(self):
        with (
            patch.object(
                AIDetectionService.primary_detector_class,
                "__init__",
                side_effect=AssertionError("transformer should not load"),
            ),
            patch.object(
                AIDetectionService.comparison_detector_class,
                "__init__",
                side_effect=AssertionError("comparison should not load"),
            ),
        ):
            result = AIDetectionService().analyze("Evidence and reasoning. " * 20)

        self.assertEqual(result["detector_name"], "ATLAS Fast Pattern Review")

    @override_settings(
        AI_DETECTION_ENGINE="transformer",
        AI_DETECTION_PRIMARY_MODEL="ShantanuT01/gradient-ai-text-detector",
        AI_DETECTION_PRIMARY_REVISION="gradient-revision",
        AI_DETECTION_ENABLE_COMPARISON=True,
        AI_DETECTION_COMPARISON_MODEL="ShantanuT01/vanguard-ai-text-detector",
        AI_DETECTION_COMPARISON_REVISION="vanguard-revision",
    )
    def test_transformer_engine_constructs_both_configured_models(self):
        service = AIDetectionService()

        self.assertIsInstance(service.primary_detector, GradientAIDetector)
        self.assertEqual(
            service.primary_detector.model_name,
            "ShantanuT01/gradient-ai-text-detector",
        )
        self.assertEqual(service.primary_detector.revision, "gradient-revision")
        self.assertIsInstance(service.comparison_detector, VanguardAIDetector)
        self.assertEqual(
            service.comparison_detector.model_name,
            "ShantanuT01/vanguard-ai-text-detector",
        )
        self.assertEqual(service.comparison_detector.revision, "vanguard-revision")

    @override_settings(
        AI_DETECTION_ENGINE="transformer",
        AI_DETECTION_FALLBACK_TO_FAST=True,
    )
    def test_transformer_failure_uses_transparent_fast_fallback(self):
        result = AIDetectionService(
            primary_detector=self.FailingDetector()
        ).analyze("Evidence and reasoning with clear limitations. " * 12)

        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["detector_name"], "ATLAS Fast Pattern Review")
        self.assertIn("Gradient transformer was unavailable", result["fallback_reason"])

    @override_settings(
        AI_DETECTION_ENGINE="transformer",
        AI_DETECTION_FALLBACK_TO_FAST=False,
    )
    def test_transformer_failure_is_reported_when_fallback_is_disabled(self):
        with self.assertRaisesMessage(AIDetectionError, "model unavailable"):
            AIDetectionService(
                primary_detector=self.FailingDetector()
            ).analyze("Evidence and reasoning. " * 12)


@override_settings(
    AI_DETECTION_ENGINE="transformer",
    AI_DETECTION_PRIMARY_MODEL="ShantanuT01/gradient-ai-text-detector",
    AI_DETECTION_ENABLE_COMPARISON=True,
    AI_DETECTION_COMPARISON_MODEL="ShantanuT01/vanguard-ai-text-detector",
)
class CheckAICommandTests(SimpleTestCase):
    @patch("library.management.commands.check_ai.AIDetectionService")
    def test_smoke_check_reports_both_model_versions(self, service_class):
        service_class.return_value.analyze.return_value = {
            "detector_name": "Gradient AI Text Detector",
            "model_version": "gradient-revision",
            "comparison_complete": True,
            "comparison": {
                "detector_name": "Vanguard AI Text Detector",
                "model_version": "vanguard-revision",
            },
        }
        output = StringIO()

        call_command("check_ai", "--run-analysis", stdout=output)

        self.assertIn(
            "Gradient AI Text Detector version gradient-revision",
            output.getvalue(),
        )
        self.assertIn(
            "Vanguard AI Text Detector version vanguard-revision",
            output.getvalue(),
        )

    @patch("library.management.commands.check_ai.AIDetectionService")
    def test_smoke_check_fails_when_comparison_is_incomplete(self, service_class):
        service_class.return_value.analyze.return_value = {
            "detector_name": "Gradient AI Text Detector",
            "model_version": "gradient-revision",
            "comparison_complete": False,
        }

        with self.assertRaisesMessage(CommandError, "Vanguard did not complete"):
            call_command("check_ai", "--run-analysis")
