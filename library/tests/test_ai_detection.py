"""Unit tests for the replaceable local AI Detection service."""

from io import BytesIO, StringIO
from math import log
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from library.services.ai_detection import (
    AIDetectionBenchmarkService,
    AIDetectionError,
    AIDetectionService,
    DesklibAcademicDetector,
    FastWritingPatternDetector,
    OnnxDistilBertDetector,
    RemoteDesklibDetector,
    VanguardAIDetector,
)
from library.services.documents import DocumentTextExtractor


class FakePipeline:
    def __init__(self, predictions, commit_hash="detector-commit-123"):
        self.predictions = predictions
        self.call_kwargs = None
        self.model = SimpleNamespace(config=SimpleNamespace(_commit_hash=commit_hash))

    def __call__(self, chunks, **kwargs):
        self.call_kwargs = kwargs
        return self.predictions


class OnnxDistilBertDetectorTests(SimpleTestCase):
    class FakeTokenizer:
        def __call__(self, texts, **kwargs):
            import numpy as np

            batch_size = len(texts)
            input_ids = np.zeros((batch_size, 256), dtype=np.int64)
            attention_mask = np.zeros((batch_size, 256), dtype=np.int64)
            attention_mask[0, :102] = 1
            attention_mask[1, :52] = 1
            return {"input_ids": input_ids, "attention_mask": attention_mask}

    class FakeSession:
        @staticmethod
        def get_inputs():
            return [
                SimpleNamespace(name="input_ids"),
                SimpleNamespace(name="attention_mask"),
            ]

        @staticmethod
        def get_outputs():
            return [SimpleNamespace(name="logits")]

        @staticmethod
        def run(output_names, inputs):
            import numpy as np

            return [np.array([[0.0, log(4)], [log(4), 0.0]], dtype=np.float32)]

    def tearDown(self):
        OnnxDistilBertDetector.release()

    def test_sections_use_token_weighted_aggregate_and_report_context(self):
        detector = OnnxDistilBertDetector(
            model_dir="models/ai_detector",
            revision="pinned-revision",
        )
        resources = (
            self.FakeTokenizer(),
            self.FakeSession(),
            {"0": "human", "1": "chatgpt"},
        )

        with (
            patch.object(detector, "_get_resources", return_value=resources),
            patch.object(detector, "_split_text", return_value=["first", "second"]),
        ):
            result = detector.analyze("A sufficiently long test sample.")

        self.assertAlmostEqual(result["ai_probability"], 60.0, places=1)
        self.assertEqual(result["chunks_analyzed"], 2)
        self.assertEqual(result["strong_ai_sections"], 1)
        self.assertEqual(result["highest_ai_section"], 1)
        self.assertAlmostEqual(result["highest_ai_probability"], 80.0, places=1)
        self.assertEqual(result["lowest_ai_section"], 2)
        self.assertAlmostEqual(result["lowest_ai_probability"], 20.0, places=1)
        self.assertEqual(result["label_mapping"], "0=human, 1=chatgpt")

    def test_missing_local_model_files_fail_with_setup_instruction(self):
        with TemporaryDirectory() as directory:
            detector = OnnxDistilBertDetector(model_dir=Path(directory))

            with self.assertRaisesMessage(
                AIDetectionError,
                "python manage.py download_ai_model",
            ):
                detector.prepare()


class DesklibAcademicDetectorTests(SimpleTestCase):
    def tearDown(self):
        DesklibAcademicDetector._pipeline = None

    def test_long_text_is_chunked_and_probabilities_are_averaged(self):
        pipeline = FakePipeline(
            [
                {"label": "LABEL_0", "score": 0.80},
                {"label": "LABEL_0", "score": 0.30},
            ]
        )
        detector = DesklibAcademicDetector()

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("word " * 300)

        self.assertEqual(result["chunks_analyzed"], 2)
        self.assertEqual(result["ai_probability"], 55.0)
        self.assertEqual(result["human_probability"], 45.0)
        self.assertEqual(result["label"], "Mixed / uncertain")
        self.assertEqual(result["detector_name"], "Desklib Academic AI Text Detector")
        self.assertEqual(
            result["model_name"],
            "desklib/ai-text-detector-academic-v1.01",
        )
        self.assertEqual(result["model_version"], "detector-commit-123")
        self.assertEqual(pipeline.call_kwargs["function_to_apply"], "sigmoid")
        self.assertEqual(pipeline.call_kwargs["batch_size"], 1)

    @override_settings(AI_DETECTION_MIN_MEMORY_MB=3072)
    def test_model_load_stops_before_oom_on_small_container(self):
        detector = DesklibAcademicDetector()

        with (
            patch(
                "library.services.ai_detection._runtime_memory_limit_mb",
                return_value=512,
            ),
            self.assertRaisesMessage(
                AIDetectionError,
                "at least 3072 MB; this runtime exposes 512 MB",
            ),
        ):
            detector._load_pipeline()

    @override_settings(AI_DETECTION_MIN_MEMORY_MB=3072)
    def test_web_request_does_not_download_uncached_model(self):
        detector = DesklibAcademicDetector(allow_download=False)

        with (
            patch(
                "library.services.ai_detection._runtime_memory_limit_mb",
                return_value=4096,
            ),
            patch(
                "library.services.ai_detection._desklib_weights_are_cached",
                return_value=False,
            ),
            self.assertRaisesMessage(AIDetectionError, "not ready in the server cache"),
        ):
            detector._load_pipeline()

    def test_low_ai_probability_reports_high_human_probability(self):
        detector = DesklibAcademicDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 0.08}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("Evidence based writing " * 40)

        self.assertEqual(result["ai_probability"], 8.0)
        self.assertEqual(result["human_probability"], 92.0)
        self.assertEqual(result["label"], "Low AI-pattern score")

    def test_single_output_is_used_as_ai_probability_regardless_of_label_name(self):
        detector = DesklibAcademicDetector()
        pipeline = FakePipeline([{"label": "LABEL_0", "score": 0.92}])

        with patch.object(detector, "_get_pipeline", return_value=pipeline):
            result = detector.analyze("A sufficiently long sample " * 30)

        self.assertEqual(result["ai_probability"], 92.0)
        self.assertEqual(result["human_probability"], 8.0)

    def test_out_of_range_probability_raises_safe_error(self):
        detector = DesklibAcademicDetector()
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


class RemoteDesklibDetectorTests(SimpleTestCase):
    token = "remote-test-token-with-at-least-32-characters"

    @staticmethod
    def result():
        return {
            "score": 73.0,
            "label": "High AI-pattern score",
            "tone": "high",
            "ai_probability": 73.0,
            "human_probability": 27.0,
            "confidence": 73.0,
            "chunks_analyzed": 1,
            "detector_name": "Desklib Academic AI Text Detector",
            "model_name": "desklib/ai-text-detector-academic-v1.01",
            "model_version": "pinned-revision",
        }

    def detector(self):
        return RemoteDesklibDetector(
            base_url="http://atlas-ai-inference:8000",
            token=self.token,
            model_name="desklib/ai-text-detector-academic-v1.01",
            revision="pinned-revision",
            timeout=90,
        )

    @patch("httpx.post")
    def test_calls_authenticated_private_service_and_accepts_pinned_model(self, post):
        expected_result = self.result()
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"result": expected_result}

        result = self.detector().analyze("Academic evidence and context. " * 5)

        self.assertEqual(result, expected_result)
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            f"Bearer {self.token}",
        )
        self.assertEqual(post.call_args.kwargs["timeout"], 90)

    @patch("httpx.post")
    def test_rejects_response_from_wrong_model(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "result": {**self.result(), "model_name": "another/model"}
        }

        with self.assertRaisesMessage(AIDetectionError, "did not use the pinned"):
            self.detector().analyze("Academic evidence and context. " * 5)

    @override_settings(
        AI_DETECTION_ENGINE="remote",
        AI_DETECTION_REMOTE_URL="http://atlas-ai-inference:8000",
        AI_DETECTION_REMOTE_TOKEN=token,
        AI_DETECTION_REMOTE_TIMEOUT=90,
        AI_DETECTION_PRIMARY_MODEL="desklib/ai-text-detector-academic-v1.01",
        AI_DETECTION_PRIMARY_REVISION="pinned-revision",
    )
    def test_remote_engine_constructs_strict_remote_detector(self):
        service = AIDetectionService()

        self.assertIsInstance(service.primary_detector, RemoteDesklibDetector)
        self.assertEqual(
            service.primary_detector.endpoint_url,
            "http://atlas-ai-inference:8000/v1/analyze",
        )

    @override_settings(
        AI_DETECTION_ENGINE="remote",
        AI_DETECTION_FALLBACK_TO_FAST=True,
    )
    def test_remote_failure_never_substitutes_fast_detector(self):
        class UnavailableRemoteDetector:
            def analyze(self, text):
                raise AIDetectionError("model unavailable")

        service = AIDetectionService(primary_detector=UnavailableRemoteDetector())

        with self.assertRaisesMessage(AIDetectionError, "model unavailable"):
            service.analyze("Academic evidence and context. " * 5)


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

    def test_desklib_and_vanguard_benchmark_results_are_reported_separately(self):
        result = AIDetectionBenchmarkService(
            primary_detector=self.StubDetector("Desklib", 61.0),
            comparison_detector=self.StubDetector("Vanguard", 58.0),
        ).analyze("sample")

        self.assertEqual(result["primary"]["detector_name"], "Desklib")
        self.assertEqual(result["primary"]["ai_probability"], 61.0)
        self.assertEqual(result["comparison"]["detector_name"], "Vanguard")
        self.assertEqual(result["comparison"]["ai_probability"], 58.0)
        self.assertTrue(result["comparison_complete"])
        self.assertFalse(result["detectors_disagree"])
        self.assertEqual(result["score_difference"], 3.0)

    def test_disagreement_is_marked_inconclusive(self):
        result = AIDetectionBenchmarkService(
            primary_detector=self.StubDetector("Desklib", 72.0),
            comparison_detector=self.StubDetector("Vanguard", 31.0),
        ).analyze("sample")

        self.assertEqual(result["label"], "Inconclusive — models disagree")
        self.assertEqual(result["tone"], "mixed")
        self.assertTrue(result["detectors_disagree"])
        self.assertEqual(result["score_difference"], 41.0)

    def test_benchmark_failure_is_reported_without_discarding_desklib(self):
        result = AIDetectionBenchmarkService(
            primary_detector=self.StubDetector("Desklib", 72.0),
            comparison_detector=self.FailingDetector(),
        ).analyze("sample")

        self.assertEqual(result["detector_name"], "Desklib")
        self.assertFalse(result["comparison_complete"])
        self.assertIn("Vanguard could not complete", result["comparison_error"])
        self.assertNotIn("comparison", result)

    def test_fast_engine_does_not_construct_transformer_detector(self):
        with patch.object(
            AIDetectionService.primary_detector_class,
            "__init__",
            side_effect=AssertionError("transformer should not load"),
        ):
            result = AIDetectionService().analyze("Evidence and reasoning. " * 20)

        self.assertEqual(result["detector_name"], "ATLAS Fast Pattern Review")

    @override_settings(
        AI_DETECTION_ENGINE="transformer",
        AI_DETECTION_PRIMARY_MODEL="desklib/ai-text-detector-academic-v1.01",
        AI_DETECTION_PRIMARY_REVISION="desklib-revision",
        AI_DETECTION_COMPARISON_MODEL="ShantanuT01/vanguard-ai-text-detector",
        AI_DETECTION_COMPARISON_REVISION="vanguard-revision",
    )
    def test_transformer_engine_constructs_only_desklib_for_live_requests(self):
        service = AIDetectionService()

        self.assertIsInstance(service.primary_detector, DesklibAcademicDetector)
        self.assertEqual(
            service.primary_detector.model_name,
            "desklib/ai-text-detector-academic-v1.01",
        )
        self.assertEqual(service.primary_detector.revision, "desklib-revision")
        self.assertFalse(service.primary_detector.allow_download)
        self.assertFalse(hasattr(service, "comparison_detector"))

        benchmark = AIDetectionBenchmarkService(
            primary_detector=self.StubDetector("Desklib", 50)
        )
        self.assertIsInstance(benchmark.comparison_detector, VanguardAIDetector)
        self.assertEqual(
            benchmark.comparison_detector.model_name,
            "ShantanuT01/vanguard-ai-text-detector",
        )
        self.assertEqual(benchmark.comparison_detector.revision, "vanguard-revision")
        self.assertFalse(benchmark.comparison_detector.allow_download)

    @override_settings(
        AI_DETECTION_ENGINE="onnx",
        AI_DETECTION_MODEL_DIR=Path("models/ai_detector"),
        AI_DETECTION_PRIMARY_MODEL="bsgcasa/ai-text-detector-distilbert",
        AI_DETECTION_PRIMARY_REVISION="pinned-revision",
    )
    def test_onnx_engine_constructs_local_int8_detector(self):
        service = AIDetectionService()

        self.assertIsInstance(service.primary_detector, OnnxDistilBertDetector)
        self.assertEqual(
            service.primary_detector.model_name,
            "bsgcasa/ai-text-detector-distilbert",
        )
        self.assertEqual(service.primary_detector.revision, "pinned-revision")

    @override_settings(
        AI_DETECTION_ENGINE="transformer",
        AI_DETECTION_FALLBACK_TO_FAST=True,
    )
    def test_transformer_failure_uses_transparent_fast_fallback(self):
        result = AIDetectionService(primary_detector=self.FailingDetector()).analyze(
            "Evidence and reasoning with clear limitations. " * 12
        )

        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["detector_name"], "ATLAS Fast Pattern Review")
        self.assertIn(
            "configured local AI model was unavailable", result["fallback_reason"]
        )

    @override_settings(
        AI_DETECTION_ENGINE="transformer",
        AI_DETECTION_FALLBACK_TO_FAST=False,
    )
    def test_transformer_failure_is_reported_when_fallback_is_disabled(self):
        with self.assertRaisesMessage(AIDetectionError, "model unavailable"):
            AIDetectionService(primary_detector=self.FailingDetector()).analyze(
                "Evidence and reasoning. " * 12
            )


@override_settings(
    AI_DETECTION_ENGINE="transformer",
    AI_DETECTION_PRIMARY_MODEL="desklib/ai-text-detector-academic-v1.01",
    AI_DETECTION_COMPARISON_MODEL="ShantanuT01/vanguard-ai-text-detector",
)
class CheckAICommandTests(SimpleTestCase):
    @patch("library.management.commands.check_ai.AIDetectionService")
    def test_smoke_check_reports_only_live_model(self, service_class):
        service_class.return_value.analyze.return_value = {
            "detector_name": "Desklib Academic AI Text Detector",
            "model_version": "desklib-revision",
        }
        output = StringIO()

        call_command("check_ai", "--run-analysis", stdout=output)

        service_class.assert_called_once_with(allow_model_download=True)
        self.assertIn(
            "Desklib Academic AI Text Detector version desklib-revision",
            output.getvalue(),
        )
        self.assertNotIn("Vanguard AI Text Detector version", output.getvalue())

    @patch("library.management.commands.check_ai.AIDetectionBenchmarkService")
    def test_explicit_benchmark_fails_when_vanguard_is_incomplete(self, service_class):
        service_class.return_value.analyze.return_value = {
            "detector_name": "Desklib Academic AI Text Detector",
            "model_version": "desklib-revision",
            "comparison_complete": False,
        }

        with self.assertRaisesMessage(CommandError, "Vanguard did not complete"):
            call_command("check_ai", "--run-analysis", "--benchmark")
        service_class.assert_called_once_with(allow_model_download=True)

    def test_benchmark_requires_analysis_flag(self):
        with self.assertRaisesMessage(CommandError, "requires --run-analysis"):
            call_command("check_ai", "--benchmark")
