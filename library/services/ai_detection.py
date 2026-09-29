"""Replaceable local detectors for administrator AI-writing analysis."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from statistics import fmean
from threading import RLock

from django.conf import settings

logger = logging.getLogger(__name__)


class AIDetectionError(RuntimeError):
    """Raised when a configured detector cannot complete an analysis."""


def _classification(ai_probability):
    if ai_probability >= 70:
        return "High AI-pattern score", "high"
    if ai_probability >= 40:
        return "Mixed / uncertain", "mixed"
    return "Low AI-pattern score", "low"


class FastWritingPatternDetector:
    """Fast, memory-safe writing-pattern estimate for modest web servers.

    This deliberately avoids loading a transformer into the Django process.
    Its result is a screening signal based on measurable writing patterns, not
    proof of authorship.  The UI communicates that limitation to reviewers.
    """

    detector_name = "ATLAS Fast Pattern Review"
    model_name = "atlas/local-writing-patterns"
    model_version = "1.0"
    words_per_chunk = 250
    transition_phrases = frozenset(
        {
            "additionally",
            "consequently",
            "furthermore",
            "however",
            "in conclusion",
            "in summary",
            "moreover",
            "nevertheless",
            "overall",
            "therefore",
            "thus",
        }
    )

    def analyze(self, text):
        if not text or not text.strip():
            raise AIDetectionError("Please provide text before starting the analysis.")

        words = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)?", text.lower())
        if not words:
            raise AIDetectionError(
                "ATLAS could not find enough readable words to analyze."
            )

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
            if sentence.strip()
        ]
        sentence_lengths = [
            len(re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)?", sentence))
            for sentence in sentences
        ]
        sentence_lengths = [length for length in sentence_lengths if length]

        # AI-like prose often has unusually regular sentence lengths, repeated
        # connective phrases, low punctuation variety, and repeated n-grams.
        # Each feature is bounded so one stylistic habit cannot dominate.
        mean_length = fmean(sentence_lengths) if sentence_lengths else len(words)
        if len(sentence_lengths) > 1 and mean_length:
            variance = fmean(
                (length - mean_length) ** 2 for length in sentence_lengths
            )
            coefficient_of_variation = math.sqrt(variance) / mean_length
        else:
            coefficient_of_variation = 0.55
        regularity = 1 - min(coefficient_of_variation / 0.75, 1)

        unique_ratio = len(set(words)) / len(words)
        expected_unique_ratio = max(0.38, 0.72 - (len(words) / 2500))
        lexical_repetition = min(
            max((expected_unique_ratio - unique_ratio) / 0.28, 0),
            1,
        )

        trigrams = list(zip(words, words[1:], words[2:], strict=False))
        repeated_trigrams = sum(
            count - 1 for count in Counter(trigrams).values() if count > 1
        )
        ngram_repetition = min(
            repeated_trigrams / max(len(trigrams) * 0.08, 1),
            1,
        )

        normalized_text = " ".join(words)
        transition_count = sum(
            len(re.findall(rf"\b{re.escape(phrase)}\b", normalized_text))
            for phrase in self.transition_phrases
        )
        transition_density = min(transition_count / max(len(words) / 80, 1), 1)

        punctuation_types = sum(mark in text for mark in ",;:-()?!")
        punctuation_simplicity = 1 - min(punctuation_types / 5, 1)

        sentence_starts = [
            match.group(0).lower()
            for sentence in sentences
            if (match := re.search(r"[A-Za-z]+", sentence))
        ]
        repeated_starts = sum(
            count - 1
            for count in Counter(sentence_starts).values()
            if count > 1
        )
        start_repetition = min(
            repeated_starts / max(len(sentence_starts) * 0.3, 1),
            1,
        )

        ai_probability = round(
            100
            * (
                0.30 * regularity
                + 0.20 * lexical_repetition
                + 0.20 * ngram_repetition
                + 0.15 * transition_density
                + 0.08 * punctuation_simplicity
                + 0.07 * start_repetition
            ),
            2,
        )
        ai_probability = min(max(ai_probability, 0), 100)
        human_probability = round(100 - ai_probability, 2)
        classification, tone = _classification(ai_probability)
        return {
            "score": ai_probability,
            "label": classification,
            "tone": tone,
            "ai_probability": ai_probability,
            "human_probability": human_probability,
            "confidence": round(max(ai_probability, human_probability), 2),
            "chunks_analyzed": max(1, math.ceil(len(words) / self.words_per_chunk)),
            "detector_name": self.detector_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
        }


class HuggingFaceDetector:
    """Shared chunking, inference, and result formatting for local detectors."""

    detector_name = "AI text detector"
    default_model_name = ""
    words_per_chunk = 250
    _pipeline = None
    _pipeline_lock = RLock()
    _inference_lock = RLock()

    def __init__(self, model_name=None, revision=None):
        self.model_name = model_name or self.default_model_name
        self.revision = (revision or "main").strip() or "main"

    def analyze(self, text):
        if not text or not text.strip():
            raise AIDetectionError("Please provide text before starting the analysis.")

        chunks = self._split_text(text)
        pipeline = self._get_pipeline()
        try:
            # Gunicorn uses threads so the large model stays loaded only once.
            # Serialize CPU inference to prevent concurrent requests from
            # oversubscribing memory and processor threads in that process.
            with type(self)._inference_lock:
                predictions = pipeline(
                    chunks,
                    truncation=True,
                    batch_size=4,
                    function_to_apply="sigmoid",
                )
        except AIDetectionError:
            raise
        except Exception as exc:
            raise AIDetectionError(
                "The local AI detector could not complete the analysis. "
                "Confirm that the configured model was downloaded successfully "
                "and try again."
            ) from exc

        if isinstance(predictions, dict):
            predictions = [predictions]
        if len(predictions) != len(chunks):
            raise AIDetectionError(
                "The local AI detector returned an incomplete result."
            )

        ai_scores = [self._ai_score(prediction) for prediction in predictions]
        ai_probability = round(fmean(ai_scores) * 100, 2)
        human_probability = round(100 - ai_probability, 2)
        classification, tone = _classification(ai_probability)
        return {
            "score": ai_probability,
            "label": classification,
            "tone": tone,
            "ai_probability": ai_probability,
            "human_probability": human_probability,
            "confidence": round(max(ai_probability, human_probability), 2),
            "chunks_analyzed": len(chunks),
            "detector_name": self.detector_name,
            "model_name": self.model_name,
            "model_version": self._model_version(pipeline),
        }

    def _load_pipeline(self):
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise AIDetectionError(
                "Local AI Detection is unavailable. Install the project requirements."
            ) from exc
        try:
            return pipeline(
                "text-classification",
                model=self.model_name,
                tokenizer=self.model_name,
                revision=self.revision,
                device=-1,
            )
        except Exception as exc:
            raise AIDetectionError(
                f"ATLAS could not load {self.detector_name}. "
                "Check the internet connection for the first model download."
            ) from exc

    def _get_pipeline(self):
        pipeline_key = (self.model_name, self.revision)
        cached = type(self)._pipeline
        if cached is not None and cached[0] == pipeline_key:
            return cached[1]
        with type(self)._pipeline_lock:
            cached = type(self)._pipeline
            if cached is None or cached[0] != pipeline_key:
                type(self)._pipeline = (pipeline_key, self._load_pipeline())
        return type(self)._pipeline[1]

    def _model_version(self, pipeline):
        model = getattr(pipeline, "model", None)
        config = getattr(model, "config", None)
        commit_hash = getattr(config, "_commit_hash", None)
        return commit_hash or self.revision

    @classmethod
    def _split_text(cls, text):
        words = text.split()
        if not words:
            raise AIDetectionError("Please provide text before starting the analysis.")
        return [
            " ".join(words[index : index + cls.words_per_chunk])
            for index in range(0, len(words), cls.words_per_chunk)
        ]


class SingleProbabilityDetector(HuggingFaceDetector):
    """Detector whose single sigmoid output is the model's P(AI)."""

    @staticmethod
    def _ai_score(prediction):
        try:
            probability = float(prediction["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AIDetectionError(
                "The local AI detector returned an invalid result."
            ) from exc
        if not 0 <= probability <= 1:
            raise AIDetectionError(
                "The local AI detector returned a confidence outside the expected range."
            )
        return probability


class GradientAIDetector(SingleProbabilityDetector):
    """Gradient's DeBERTa-v3-large AI-text detector."""

    detector_name = "Gradient AI Text Detector"
    default_model_name = "ShantanuT01/gradient-ai-text-detector"


class VanguardAIDetector(SingleProbabilityDetector):
    """Vanguard's ModernBERT-large AI-text detector."""

    detector_name = "Vanguard AI Text Detector"
    default_model_name = "ShantanuT01/vanguard-ai-text-detector"


class AIDetectionService:
    """Run Gradient and compare its result with Vanguard when configured."""

    primary_detector_class = GradientAIDetector
    comparison_detector_class = VanguardAIDetector

    def __init__(self, primary_detector=None, comparison_detector=None):
        if primary_detector is not None:
            self.primary_detector = primary_detector
        elif settings.AI_DETECTION_ENGINE == "fast":
            self.primary_detector = FastWritingPatternDetector()
        elif settings.AI_DETECTION_ENGINE == "transformer":
            self.primary_detector = self.primary_detector_class(
                model_name=settings.AI_DETECTION_PRIMARY_MODEL,
                revision=settings.AI_DETECTION_PRIMARY_REVISION,
            )
        else:
            raise AIDetectionError(
                "AI_DETECTION_ENGINE must be either 'fast' or 'transformer'."
            )
        if comparison_detector is not None:
            self.comparison_detector = comparison_detector
        elif (
            settings.AI_DETECTION_ENGINE == "transformer"
            and settings.AI_DETECTION_ENABLE_COMPARISON
        ):
            self.comparison_detector = self.comparison_detector_class(
                model_name=settings.AI_DETECTION_COMPARISON_MODEL,
                revision=settings.AI_DETECTION_COMPARISON_REVISION,
            )
        else:
            self.comparison_detector = None

    def analyze(self, text):
        try:
            result = self.primary_detector.analyze(text)
        except AIDetectionError as error:
            if not (
                settings.AI_DETECTION_ENGINE == "transformer"
                and settings.AI_DETECTION_FALLBACK_TO_FAST
            ):
                raise
            logger.warning(
                "The configured transformer detector failed; using fast review: %s",
                error,
            )
            result = FastWritingPatternDetector().analyze(text)
            result["fallback_used"] = True
            result["fallback_reason"] = (
                "The Gradient transformer was unavailable for this analysis."
            )
            return result

        if self.comparison_detector is None:
            return result

        try:
            comparison = self.comparison_detector.analyze(text)
        except AIDetectionError as error:
            logger.warning("The comparison detector failed: %s", error)
            result["comparison_complete"] = False
            result["comparison_error"] = (
                "Vanguard could not complete this comparison. Treat the Gradient "
                "result as a single-model screening result and check server AI health."
            )
            return result

        primary = dict(result)
        detectors_disagree = (primary["ai_probability"] > 50) != (
            comparison["ai_probability"] > 50
        )
        result["primary"] = primary
        result["comparison"] = comparison
        result["comparison_complete"] = True
        result["detectors_disagree"] = detectors_disagree
        result["score_difference"] = round(
            abs(primary["ai_probability"] - comparison["ai_probability"]),
            2,
        )
        if detectors_disagree:
            result["comparison_status"] = (
                "The models fall on opposite sides of the 50% screening threshold."
            )
            result["label"] = "Inconclusive — models disagree"
            result["tone"] = "mixed"
        elif primary["ai_probability"] > 50:
            result["comparison_status"] = (
                "Both models are on the AI-pattern side of the 50% threshold."
            )
        else:
            result["comparison_status"] = (
                "Both models are on the human-pattern side of the 50% threshold."
            )
        return result
