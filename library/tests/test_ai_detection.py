"""Unit tests for the local RoBERTa AI Detection service."""

from unittest.mock import patch

from django.test import SimpleTestCase

from library.services.ai_detection import AIDetectionError, RobertaAIDetector


class RobertaAIDetectorTests(SimpleTestCase):
    def tearDown(self):
        RobertaAIDetector._pipeline = None

    def test_long_text_is_chunked_and_probabilities_are_averaged(self):
        predictions = [
            {"label": "Fake", "score": 0.80},
            {"label": "Real", "score": 0.70},
        ]
        fake_pipeline = lambda chunks, **kwargs: predictions
        detector = RobertaAIDetector()

        with patch.object(detector, "_get_pipeline", return_value=fake_pipeline):
            result = detector.analyze("word " * 300)

        self.assertEqual(result["chunks_analyzed"], 2)
        self.assertEqual(result["ai_probability"], 55.0)
        self.assertEqual(result["human_probability"], 45.0)
        self.assertEqual(result["label"], "Mixed / uncertain")

    def test_real_label_is_converted_to_inverse_ai_probability(self):
        detector = RobertaAIDetector()
        fake_pipeline = lambda chunks, **kwargs: [{"label": "Real", "score": 0.92}]

        with patch.object(detector, "_get_pipeline", return_value=fake_pipeline):
            result = detector.analyze("Evidence based writing " * 40)

        self.assertEqual(result["ai_probability"], 8.0)
        self.assertEqual(result["human_probability"], 92.0)
        self.assertEqual(result["label"], "Low AI likelihood")

    def test_unknown_model_label_raises_safe_error(self):
        detector = RobertaAIDetector()
        fake_pipeline = lambda chunks, **kwargs: [{"label": "LABEL_0", "score": 0.9}]

        with patch.object(detector, "_get_pipeline", return_value=fake_pipeline):
            with self.assertRaisesMessage(
                AIDetectionError,
                "unknown classification",
            ):
                detector.analyze("A sufficiently long sample " * 30)
