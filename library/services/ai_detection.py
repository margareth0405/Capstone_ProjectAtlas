"""Replaceable local detectors for administrator AI-writing analysis."""

from __future__ import annotations

import math
import re
from collections import Counter
from statistics import fmean
from threading import RLock

from django.conf import settings


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

        trigrams = list(zip(words, words[1:], words[2:]))
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


class AcademicBertDetector(HuggingFaceDetector):
    """Primary BERT detector optimized for English academic paragraphs."""

    detector_name = "Academic BERT"
    default_model_name = "followsci/bert-ai-text-detector"

    @staticmethod
    def _ai_score(prediction):
        try:
            label = str(prediction["label"]).strip().lower().replace("-", "_")
            probability = float(prediction["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AIDetectionError(
                "The local AI detector returned an invalid result."
            ) from exc
        if not 0 <= probability <= 1:
            raise AIDetectionError(
                "The local AI detector returned a confidence outside the expected range."
            )
        if label in {"label_1", "ai", "ai_generated"}:
            return probability
        if label in {"label_0", "human", "human_written"}:
            return 1 - probability
        raise AIDetectionError(
            "The local AI detector returned an unknown classification."
        )


class DesklibAcademicDetector(HuggingFaceDetector):
    """Optional academic-domain validator using the publisher's custom head."""

    detector_name = "Desklib Academic"
    default_model_name = "desklib/ai-text-detector-academic-v1.01"

    @staticmethod
    def _ai_score(prediction):
        try:
            probability = float(prediction["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AIDetectionError(
                "The validation detector returned an invalid result."
            ) from exc
        if not 0 <= probability <= 1:
            raise AIDetectionError(
                "The validation detector returned a confidence outside the expected range."
            )
        return probability

    def _load_pipeline(self):
        try:
            import torch
            from torch import nn
            from transformers import (
                AutoConfig,
                AutoModel,
                AutoTokenizer,
                PreTrainedModel,
            )
        except ImportError as exc:
            raise AIDetectionError(
                "Academic validation is unavailable. Install the project requirements."
            ) from exc

        model_name = self.model_name
        revision = self.revision

        class AcademicDetectionModel(PreTrainedModel):
            config_class = AutoConfig

            def __init__(self, config):
                super().__init__(config)
                self.model = AutoModel.from_config(config)
                self.classifier = nn.Linear(config.hidden_size, 1)
                self.init_weights()

            def forward(self, input_ids, attention_mask=None, labels=None):
                # Transformers may supply labels through the standard model
                # interface; inference only needs the encoded inputs.
                del labels
                outputs = self.model(input_ids, attention_mask=attention_mask)
                hidden_state = outputs[0]
                expanded_mask = attention_mask.unsqueeze(-1).expand(
                    hidden_state.size()
                ).float()
                pooled = (hidden_state * expanded_mask).sum(dim=1) / torch.clamp(
                    expanded_mask.sum(dim=1), min=1e-9
                )
                logits = self.classifier(pooled)
                return {"logits": logits}

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
            model = AcademicDetectionModel.from_pretrained(
                model_name,
                revision=revision,
            )
            model.to(torch.device("cpu"))
            model.eval()
        except Exception as exc:
            raise AIDetectionError(
                "ATLAS could not load Desklib Academic. Check the internet "
                "connection for the first model download."
            ) from exc

        class AcademicPipeline:
            def __init__(self, loaded_model, loaded_tokenizer):
                self.model = loaded_model
                self.tokenizer = loaded_tokenizer

            def __call__(self, chunks, truncation=True, batch_size=4):
                predictions = []
                for index in range(0, len(chunks), batch_size):
                    batch = chunks[index : index + batch_size]
                    encoded = self.tokenizer(
                        batch,
                        padding=True,
                        truncation=truncation,
                        max_length=768,
                        return_tensors="pt",
                    )
                    with torch.no_grad():
                        logits = self.model(**encoded)["logits"].view(-1)
                        probabilities = torch.sigmoid(logits).tolist()
                    predictions.extend(
                        {"label": "ai_generated", "score": probability}
                        for probability in probabilities
                    )
                return predictions

        return AcademicPipeline(model, tokenizer)


class AIDetectionService:
    """Run the configured primary detector and optional academic validation."""

    primary_detector_class = AcademicBertDetector
    validation_detector_class = DesklibAcademicDetector

    def __init__(self, primary_detector=None, validation_detector=None):
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
        if validation_detector is not None:
            self.validation_detector = validation_detector
        elif settings.AI_DETECTION_ENABLE_VALIDATION:
            self.validation_detector = self.validation_detector_class(
                model_name=settings.AI_DETECTION_VALIDATION_MODEL,
                revision=settings.AI_DETECTION_VALIDATION_REVISION,
            )
        else:
            self.validation_detector = None

    def analyze(self, text):
        result = self.primary_detector.analyze(text)
        if self.validation_detector is not None:
            validation = self.validation_detector.analyze(text)
            detectors_disagree = (
                result["ai_probability"] >= 50
            ) != (validation["ai_probability"] >= 50)
            validation["agrees_with_primary"] = not detectors_disagree
            result["validation"] = validation
            result["detectors_disagree"] = detectors_disagree
            if detectors_disagree:
                result["label"] = "Uncertain — detectors disagree"
                result["tone"] = "mixed"
        return result
