"""Replaceable local detectors for administrator AI-writing analysis."""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path
from statistics import fmean
from threading import RLock
from urllib.parse import urlsplit

from django.conf import settings

logger = logging.getLogger(__name__)


def _runtime_memory_limit_mb():
    """Return the effective host/container memory limit when it is discoverable."""

    limits = []
    for path in (
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
    ):
        try:
            with open(path, encoding="ascii") as memory_file:
                raw_value = memory_file.read().strip()
            if raw_value and raw_value != "max":
                value = int(raw_value)
                # Some cgroup v1 hosts expose an enormous sentinel for no limit.
                if 0 < value < 2**60:
                    limits.append(value)
        except (OSError, ValueError):
            continue

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
        physical_memory = page_size * page_count
        if physical_memory > 0:
            limits.append(physical_memory)
    except (AttributeError, OSError, ValueError):
        pass

    if not limits:
        return None
    return max(1, min(limits) // (1024 * 1024))


def _desklib_weights_are_cached(model_name, revision):
    """Check for the pinned weights without contacting Hugging Face."""

    try:
        from huggingface_hub import try_to_load_from_cache

        cached_path = try_to_load_from_cache(
            model_name,
            "model.safetensors",
            revision=revision,
        )
    except (ImportError, OSError, ValueError):
        return False
    return isinstance(cached_path, str) and os.path.isfile(cached_path)


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
            variance = fmean((length - mean_length) ** 2 for length in sentence_lengths)
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
            count - 1 for count in Counter(sentence_starts).values() if count > 1
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


class OnnxDistilBertDetector:
    """Run the pinned, INT8 DistilBERT detector without PyTorch."""

    detector_name = "DistilBERT ONNX AI Text Detector"
    default_model_name = "bsgcasa/ai-text-detector-distilbert"
    model_filename = "model_int8.onnx"
    model_sha256 = "28273c934ba800bb63346db125ecc0b7ed859e586ef9440b76585cc158c8a4d8"
    label_filename = "label_order.json"
    tokenizer_filenames = ("tokenizer.json", "tokenizer_config.json")
    max_length = 256
    batch_size = 4
    strong_ai_threshold = 0.70
    _resources = None
    _resources_lock = RLock()
    _inference_lock = RLock()

    def __init__(self, model_dir, model_name=None, revision=None):
        self.model_dir = Path(model_dir)
        self.model_name = model_name or self.default_model_name
        self.revision = (revision or "main").strip() or "main"

    def analyze(self, text):
        if not text or not text.strip():
            raise AIDetectionError("Please provide text before starting the analysis.")

        tokenizer, session, labels = self._get_resources()
        chunks = self._split_text(tokenizer, text)
        ai_scores = []
        token_weights = []

        try:
            import numpy as np

            with type(self)._inference_lock:
                for index in range(0, len(chunks), self.batch_size):
                    batch = chunks[index : index + self.batch_size]
                    encoded = tokenizer(
                        batch,
                        return_tensors="np",
                        padding="max_length",
                        truncation=True,
                        max_length=self.max_length,
                    )
                    inputs = {
                        item.name: encoded[item.name].astype(np.int64, copy=False)
                        for item in session.get_inputs()
                        if item.name in encoded
                    }
                    if {"input_ids", "attention_mask"} - inputs.keys():
                        raise AIDetectionError(
                            "The local ONNX detector has unexpected model inputs."
                        )
                    logits = session.run([session.get_outputs()[0].name], inputs)[0]
                    if logits.ndim != 2 or logits.shape[1] != 2:
                        raise AIDetectionError(
                            "The local ONNX detector returned an unexpected result."
                        )
                    normalized = logits - np.max(logits, axis=1, keepdims=True)
                    exp_logits = np.exp(normalized)
                    probabilities = exp_logits / exp_logits.sum(axis=1, keepdims=True)
                    ai_scores.extend(float(value) for value in probabilities[:, 1])
                    token_weights.extend(
                        max(int(value) - 2, 1)
                        for value in encoded["attention_mask"].sum(axis=1)
                    )
        except AIDetectionError:
            raise
        except Exception as exc:
            raise AIDetectionError(
                "The local ONNX detector could not complete the analysis."
            ) from exc

        if len(ai_scores) != len(chunks):
            raise AIDetectionError(
                "The local ONNX detector returned an incomplete result."
            )

        weighted_probability = sum(
            score * weight
            for score, weight in zip(ai_scores, token_weights, strict=True)
        ) / sum(token_weights)
        ai_probability = round(weighted_probability * 100, 2)
        human_probability = round(100 - ai_probability, 2)
        classification, tone = _classification(ai_probability)
        highest_index, highest_score = max(
            enumerate(ai_scores, start=1), key=lambda x: x[1]
        )
        lowest_index, lowest_score = min(
            enumerate(ai_scores, start=1), key=lambda x: x[1]
        )
        strong_sections = sum(score >= self.strong_ai_threshold for score in ai_scores)
        return {
            "score": ai_probability,
            "label": classification,
            "tone": tone,
            "ai_probability": ai_probability,
            "human_probability": human_probability,
            "confidence": round(max(ai_probability, human_probability), 2),
            "chunks_analyzed": len(chunks),
            "strong_ai_sections": strong_sections,
            "highest_ai_section": highest_index,
            "highest_ai_probability": round(highest_score * 100, 2),
            "lowest_ai_section": lowest_index,
            "lowest_ai_probability": round(lowest_score * 100, 2),
            "aggregation_method": "Token-weighted section average",
            "detector_name": self.detector_name,
            "model_name": self.model_name,
            "model_version": self.revision,
            "label_mapping": f"0={labels['0']}, 1={labels['1']}",
        }

    def _get_resources(self):
        resource_key = str(self.model_dir.resolve())
        cached = type(self)._resources
        if cached is not None and cached[0] == resource_key:
            return cached[1]
        with type(self)._resources_lock:
            cached = type(self)._resources
            if cached is None or cached[0] != resource_key:
                type(self)._resources = (resource_key, self._load_resources())
        return type(self)._resources[1]

    def _load_resources(self):
        required_files = (
            self.model_filename,
            self.label_filename,
            *self.tokenizer_filenames,
        )
        missing = [
            name for name in required_files if not (self.model_dir / name).is_file()
        ]
        if missing:
            raise AIDetectionError(
                "The local INT8 AI model is not installed. Run "
                "'python manage.py download_ai_model' on the development computer, "
                "then include the models/ai_detector files in the deployment."
            )

        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise AIDetectionError(
                "Local AI Detection is unavailable. Install the project requirements."
            ) from exc

        try:
            with (self.model_dir / self.label_filename).open(encoding="utf-8") as file:
                labels = json.load(file)
            if labels != {"0": "human", "1": "chatgpt"}:
                raise ValueError("unexpected label mapping")

            digest = hashlib.sha256()
            with (self.model_dir / self.model_filename).open("rb") as model_file:
                for block in iter(lambda: model_file.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != self.model_sha256:
                raise ValueError("unexpected ONNX model checksum")

            tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )
            if not getattr(tokenizer, "is_fast", False):
                raise ValueError("a fast tokenizer is required for lossless chunking")

            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            session = ort.InferenceSession(
                str(self.model_dir / self.model_filename),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            input_names = {item.name for item in session.get_inputs()}
            output_names = {item.name for item in session.get_outputs()}
            if not {"input_ids", "attention_mask"}.issubset(input_names):
                raise ValueError("unexpected model inputs")
            if "logits" not in output_names:
                raise ValueError("unexpected model output")
        except Exception as exc:
            raise AIDetectionError(
                "ATLAS could not load the pinned DistilBERT INT8 model files. "
                "Download a clean copy and try again."
            ) from exc
        return tokenizer, session, labels

    @classmethod
    def _split_text(cls, tokenizer, text):
        encoded = tokenizer(
            text,
            add_special_tokens=False,
            return_attention_mask=False,
            return_offsets_mapping=True,
            truncation=False,
            verbose=False,
        )
        offsets = encoded.get("offset_mapping", [])
        if not offsets:
            raise AIDetectionError(
                "ATLAS could not find enough readable text to analyze."
            )

        payload_size = cls.max_length - tokenizer.num_special_tokens_to_add(pair=False)
        chunks = []
        for index in range(0, len(offsets), payload_size):
            group = offsets[index : index + payload_size]
            chunk = text[group[0][0] : group[-1][1]].strip()
            if chunk:
                chunks.append(chunk)
        if not chunks:
            raise AIDetectionError(
                "ATLAS could not find enough readable text to analyze."
            )
        return chunks

    def prepare(self):
        """Load and validate the tokenizer and ONNX session."""

        self._get_resources()

    @classmethod
    def release(cls):
        cls._resources = None
        gc.collect()


class HuggingFaceDetector:
    """Shared chunking, inference, and result formatting for local detectors."""

    detector_name = "AI text detector"
    default_model_name = ""
    words_per_chunk = 250
    batch_size = 4
    _pipeline = None
    _pipeline_lock = RLock()
    _inference_lock = RLock()

    def __init__(self, model_name=None, revision=None, *, allow_download=True):
        self.model_name = model_name or self.default_model_name
        self.revision = (revision or "main").strip() or "main"
        self.allow_download = allow_download

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
                    batch_size=self.batch_size,
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

    def prepare(self):
        """Load and cache model resources before serving inference requests."""

        self._get_pipeline()

    @classmethod
    def release(cls):
        """Release cached model memory after a one-off benchmark."""

        cls._pipeline = None
        gc.collect()

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


class _DesklibInferencePipeline:
    """Small adapter matching the callable used by the shared detector."""

    def __init__(self, model, tokenizer, torch_module):
        self.model = model
        self.tokenizer = tokenizer
        self.torch = torch_module

    def __call__(self, chunks, *, batch_size=4, **unused_options):
        predictions = []
        maximum_length = min(
            int(getattr(self.model.config, "max_position_embeddings", 512)),
            512,
        )
        for index in range(0, len(chunks), batch_size):
            batch = chunks[index : index + batch_size]
            encoded = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=maximum_length,
                return_tensors="pt",
            )
            with self.torch.no_grad():
                outputs = self.model(
                    input_ids=encoded["input_ids"],
                    attention_mask=encoded["attention_mask"],
                )
                probabilities = self.torch.sigmoid(outputs["logits"].view(-1))
            predictions.extend(
                {"label": "LABEL_0", "score": probability.item()}
                for probability in probabilities
            )
        return predictions


class DesklibAcademicDetector(SingleProbabilityDetector):
    """Desklib's academic DeBERTa detector with its published custom head."""

    detector_name = "Desklib Academic AI Text Detector"
    default_model_name = "desklib/ai-text-detector-academic-v1.01"
    batch_size = 1

    def _load_pipeline(self):
        memory_limit_mb = _runtime_memory_limit_mb()
        minimum_memory_mb = settings.AI_DETECTION_MIN_MEMORY_MB
        if memory_limit_mb is not None and memory_limit_mb < minimum_memory_mb:
            raise AIDetectionError(
                "The Desklib model needs a larger server memory allocation "
                f"(at least {minimum_memory_mb} MB; this runtime exposes "
                f"{memory_limit_mb} MB)."
            )
        if not self.allow_download and not _desklib_weights_are_cached(
            self.model_name,
            self.revision,
        ):
            raise AIDetectionError(
                "The pinned Desklib model is not ready in the server cache. "
                "Run 'python manage.py check_ai --run-analysis' from the "
                "deployment shell to download and verify it."
            )
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
                "Local AI Detection is unavailable. Install the project requirements."
            ) from exc

        class DesklibAIDetectionModel(PreTrainedModel):
            config_class = AutoConfig

            def __init__(self, config):
                super().__init__(config)
                self.model = AutoModel.from_config(config)
                self.classifier = nn.Linear(config.hidden_size, 1)
                self.post_init()

            def forward(self, input_ids, attention_mask=None):
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                )
                last_hidden_state = outputs[0]
                expanded_mask = (
                    attention_mask.unsqueeze(-1)
                    .expand(last_hidden_state.size())
                    .float()
                )
                pooled_output = torch.sum(
                    last_hidden_state * expanded_mask, dim=1
                ) / torch.clamp(expanded_mask.sum(dim=1), min=1e-9)
                return {"logits": self.classifier(pooled_output)}

        try:
            config = AutoConfig.from_pretrained(
                self.model_name,
                revision=self.revision,
                local_files_only=not self.allow_download,
            )
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                revision=self.revision,
                local_files_only=not self.allow_download,
            )
            model = DesklibAIDetectionModel.from_pretrained(
                self.model_name,
                config=config,
                revision=self.revision,
                local_files_only=not self.allow_download,
            )
            model.eval()
        except Exception as exc:
            if not self.allow_download:
                raise AIDetectionError(
                    "The pinned Desklib model is not ready in the server cache. "
                    "Run 'python manage.py check_ai --run-analysis' from the "
                    "deployment shell to download and verify it."
                ) from exc
            raise AIDetectionError(
                "ATLAS could not load the Desklib Academic AI Text Detector. "
                "Check the internet connection for the first model download."
            ) from exc
        return _DesklibInferencePipeline(model, tokenizer, torch)


class VanguardAIDetector(SingleProbabilityDetector):
    """Vanguard's ModernBERT-large AI-text detector."""

    detector_name = "Vanguard AI Text Detector"
    default_model_name = "ShantanuT01/vanguard-ai-text-detector"


class RemoteDesklibDetector:
    """Call the authenticated dedicated Desklib inference service."""

    detector_name = "Desklib Academic AI Text Detector"

    def __init__(self, base_url, token, model_name, revision, timeout=180):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise AIDetectionError(
                "AI_DETECTION_REMOTE_URL must be a valid HTTP or HTTPS service URL."
            )
        if len(token) < 32:
            raise AIDetectionError(
                "AI_DETECTION_REMOTE_TOKEN must contain at least 32 characters."
            )
        self.endpoint_url = base_url.rstrip("/") + "/v1/analyze"
        self.token = token
        self.model_name = model_name
        self.revision = revision
        self.timeout = timeout

    def analyze(self, text):
        if not text or not text.strip():
            raise AIDetectionError("Please provide text before starting the analysis.")
        try:
            import httpx
        except ImportError as exc:
            raise AIDetectionError(
                "The dedicated Desklib client dependency is unavailable."
            ) from exc

        try:
            response = httpx.post(
                self.endpoint_url,
                json={"text": text},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise AIDetectionError(
                "The dedicated Desklib service is unavailable. Try again shortly."
            ) from exc

        if response.status_code != 200:
            detail = ""
            try:
                detail = str(response.json().get("error", "")).strip()
            except (TypeError, ValueError):
                pass
            if response.status_code == 503 and detail:
                raise AIDetectionError(detail)
            raise AIDetectionError(
                "The dedicated Desklib service could not complete the analysis."
            )
        try:
            result = response.json()["result"]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIDetectionError(
                "The dedicated Desklib service returned an invalid response."
            ) from exc

        self._validate_result(result)
        return result

    def _validate_result(self, result):
        if not isinstance(result, dict):
            raise AIDetectionError(
                "The dedicated Desklib service returned an invalid response."
            )
        if (
            result.get("detector_name") != self.detector_name
            or result.get("model_name") != self.model_name
            or result.get("model_version") != self.revision
        ):
            raise AIDetectionError(
                "The dedicated AI service did not use the pinned Desklib model."
            )
        required_numbers = (
            "score",
            "ai_probability",
            "human_probability",
            "confidence",
            "chunks_analyzed",
        )
        if any(
            isinstance(result.get(name), bool)
            or not isinstance(result.get(name), (int, float))
            for name in required_numbers
        ):
            raise AIDetectionError(
                "The dedicated Desklib service returned an invalid response."
            )
        probability_fields = (
            "score",
            "ai_probability",
            "human_probability",
            "confidence",
        )
        if any(not 0 <= float(result[name]) <= 100 for name in probability_fields):
            raise AIDetectionError(
                "The dedicated Desklib service returned an invalid probability."
            )
        if (
            not isinstance(result["chunks_analyzed"], int)
            or result["chunks_analyzed"] < 1
        ):
            raise AIDetectionError(
                "The dedicated Desklib service returned an invalid response."
            )


class AIDetectionService:
    """Run only the configured live detector for administrator requests."""

    primary_detector_class = OnnxDistilBertDetector
    transformer_detector_class = DesklibAcademicDetector
    remote_detector_class = RemoteDesklibDetector

    def __init__(self, primary_detector=None, *, allow_model_download=False):
        if primary_detector is not None:
            self.primary_detector = primary_detector
        elif settings.AI_DETECTION_ENGINE == "fast":
            self.primary_detector = FastWritingPatternDetector()
        elif settings.AI_DETECTION_ENGINE == "onnx":
            self.primary_detector = self.primary_detector_class(
                model_dir=settings.AI_DETECTION_MODEL_DIR,
                model_name=settings.AI_DETECTION_PRIMARY_MODEL,
                revision=settings.AI_DETECTION_PRIMARY_REVISION,
            )
        elif settings.AI_DETECTION_ENGINE == "transformer":
            self.primary_detector = self.transformer_detector_class(
                model_name=settings.AI_DETECTION_PRIMARY_MODEL,
                revision=settings.AI_DETECTION_PRIMARY_REVISION,
                allow_download=allow_model_download,
            )
        elif settings.AI_DETECTION_ENGINE == "remote":
            self.primary_detector = self.remote_detector_class(
                base_url=settings.AI_DETECTION_REMOTE_URL,
                token=settings.AI_DETECTION_REMOTE_TOKEN,
                model_name=settings.AI_DETECTION_PRIMARY_MODEL,
                revision=settings.AI_DETECTION_PRIMARY_REVISION,
                timeout=settings.AI_DETECTION_REMOTE_TIMEOUT,
            )
        else:
            raise AIDetectionError(
                "AI_DETECTION_ENGINE must be 'onnx', 'fast', 'transformer', or 'remote'."
            )

    def analyze(self, text):
        try:
            result = self.primary_detector.analyze(text)
        except AIDetectionError as error:
            if not (
                settings.AI_DETECTION_ENGINE in {"onnx", "transformer"}
                and settings.AI_DETECTION_FALLBACK_TO_FAST
            ):
                raise
            logger.warning(
                "The configured AI detector failed; using fast review: %s",
                error,
            )
            result = FastWritingPatternDetector().analyze(text)
            result["fallback_used"] = True
            result["fallback_reason"] = (
                "The configured local AI model was unavailable for this analysis. "
                f"{error}"
            )
        return result


class AIDetectionBenchmarkService:
    """Compare Desklib with Vanguard only during an explicit benchmark."""

    comparison_detector_class = VanguardAIDetector

    def __init__(
        self,
        primary_detector=None,
        comparison_detector=None,
        *,
        allow_model_download=False,
    ):
        self.primary_service = AIDetectionService(
            primary_detector=primary_detector,
            allow_model_download=allow_model_download,
        )
        self.comparison_detector = (
            comparison_detector
            or self.comparison_detector_class(
                model_name=settings.AI_DETECTION_COMPARISON_MODEL,
                revision=settings.AI_DETECTION_COMPARISON_REVISION,
                allow_download=allow_model_download,
            )
        )

    @staticmethod
    def _release(detector):
        release = getattr(detector, "release", None)
        if callable(release):
            release()

    def analyze(self, text):
        primary = self.primary_service.analyze(text)
        if primary.get("fallback_used"):
            primary["comparison_complete"] = False
            primary["comparison_error"] = (
                "Vanguard was not started because Desklib used the fast fallback."
            )
            return primary

        # Run the large models sequentially and release Desklib before loading
        # Vanguard so a benchmark does not keep both models in memory.
        self._release(self.primary_service.primary_detector)
        try:
            comparison = self.comparison_detector.analyze(text)
        except AIDetectionError as error:
            logger.warning("The benchmark detector failed: %s", error)
            primary["comparison_complete"] = False
            primary["comparison_error"] = (
                "Vanguard could not complete this benchmark. Treat the Desklib "
                "result as a single-model screening result."
            )
            return primary
        finally:
            self._release(self.comparison_detector)

        result = dict(primary)
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
