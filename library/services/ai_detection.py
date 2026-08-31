"""Local RoBERTa service for administrator AI writing analysis."""

from statistics import fmean
from threading import RLock


class AIDetectionError(RuntimeError):
    """Raised when the local detector cannot complete an analysis."""


class RobertaAIDetector:
    """Analyze bounded text chunks with the local GPT-2 output detector."""

    model_name = "openai-community/roberta-base-openai-detector"
    words_per_chunk = 250
    _pipeline = None
    _pipeline_lock = RLock()

    def analyze(self, text):
        if not text or not text.strip():
            raise AIDetectionError("Please provide text before starting the analysis.")

        chunks = self._split_text(text)
        try:
            predictions = self._get_pipeline()(
                chunks,
                truncation=True,
                batch_size=4,
            )
        except AIDetectionError:
            raise
        except Exception as exc:
            raise AIDetectionError(
                "The local AI detector could not complete the analysis. "
                "Confirm that the model was downloaded successfully and try again."
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
        classification, tone = self._classification(ai_probability)
        return {
            "score": ai_probability,
            "label": classification,
            "tone": tone,
            "ai_probability": ai_probability,
            "human_probability": human_probability,
            "confidence": round(max(ai_probability, human_probability), 2),
            "chunks_analyzed": len(chunks),
            "model_name": self.model_name,
        }

    @classmethod
    def _get_pipeline(cls):
        if cls._pipeline is not None:
            return cls._pipeline
        with cls._pipeline_lock:
            if cls._pipeline is None:
                try:
                    from transformers import pipeline
                except ImportError as exc:
                    raise AIDetectionError(
                        "Local AI Detection is unavailable. "
                        "Install the project requirements."
                    ) from exc
                try:
                    cls._pipeline = pipeline(
                        "text-classification",
                        model=cls.model_name,
                        tokenizer=cls.model_name,
                        device=-1,
                    )
                except Exception as exc:
                    raise AIDetectionError(
                        "ATLAS could not load the local RoBERTa detector. "
                        "Check the internet connection for the first model download."
                    ) from exc
        return cls._pipeline

    @classmethod
    def _split_text(cls, text):
        words = text.split()
        if not words:
            raise AIDetectionError("Please provide text before starting the analysis.")
        return [
            " ".join(words[index : index + cls.words_per_chunk])
            for index in range(0, len(words), cls.words_per_chunk)
        ]

    @staticmethod
    def _ai_score(prediction):
        try:
            label = str(prediction["label"]).strip().lower()
            confidence = float(prediction["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AIDetectionError(
                "The local AI detector returned an invalid result."
            ) from exc
        if not 0 <= confidence <= 1:
            raise AIDetectionError(
                "The local AI detector returned a confidence outside the expected range."
            )
        if label == "fake":
            return confidence
        if label == "real":
            return 1 - confidence
        raise AIDetectionError(
            "The local AI detector returned an unknown classification."
        )

    @staticmethod
    def _classification(ai_probability):
        if ai_probability >= 70:
            return "High AI likelihood", "high"
        if ai_probability >= 40:
            return "Mixed / uncertain", "mixed"
        return "Low AI likelihood", "low"
