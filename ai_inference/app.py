"""Minimal WSGI application that exposes only health and Desklib inference."""

from __future__ import annotations

import hmac
import json
import logging
from threading import Lock, Thread

from library.services.ai_detection import AIDetectionError

logger = logging.getLogger(__name__)


class ModelState:
    """Load one detector in the background and expose explicit readiness."""

    def __init__(self, detector):
        self.detector = detector
        self.status = "starting"
        self.error = ""
        self._start_lock = Lock()

    def start(self):
        with self._start_lock:
            if self.status != "starting":
                return
            self.status = "loading"
            Thread(target=self._load, name="desklib-loader", daemon=True).start()

    def _load(self):
        try:
            self.detector.prepare()
        except Exception as exc:
            logger.exception("The dedicated Desklib model failed to load")
            self.error = str(exc)
            self.status = "error"
        else:
            self.status = "ready"

    def analyze(self, text):
        if self.status == "loading":
            raise AIDetectionError(
                "The dedicated Desklib service is still loading its model. "
                "Try again shortly."
            )
        if self.status != "ready":
            raise AIDetectionError(
                "The dedicated Desklib service could not load its pinned model. "
                "Check the inference-service logs."
            )
        return self.detector.analyze(text)


class InferenceApplication:
    """Serve a bounded, token-authenticated JSON inference API."""

    maximum_body_bytes = 100_000
    minimum_text_characters = 100
    maximum_text_characters = 20_000

    def __init__(self, state, token):
        if len(token) < 32:
            raise RuntimeError("AI_INFERENCE_TOKEN must contain at least 32 characters.")
        self.state = state
        self.token = token
        self.state.start()

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        if method == "GET" and path == "/health":
            return self._json(
                start_response,
                "200 OK",
                {"status": self.state.status},
            )
        if method != "POST" or path != "/v1/analyze":
            return self._json(start_response, "404 Not Found", {"error": "Not found."})
        if not self._authorized(environ):
            return self._json(
                start_response,
                "401 Unauthorized",
                {"error": "Unauthorized."},
            )
        if not environ.get("CONTENT_TYPE", "").lower().startswith("application/json"):
            return self._json(
                start_response,
                "415 Unsupported Media Type",
                {"error": "Send application/json."},
            )
        try:
            content_length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            content_length = 0
        if not 0 < content_length <= self.maximum_body_bytes:
            return self._json(
                start_response,
                "413 Payload Too Large",
                {"error": "The request body is missing or too large."},
            )
        try:
            payload = json.loads(environ["wsgi.input"].read(content_length))
            text = payload["text"]
        except (KeyError, TypeError, UnicodeDecodeError, ValueError):
            return self._json(
                start_response,
                "400 Bad Request",
                {"error": "Provide a valid JSON text field."},
            )
        if not isinstance(text, str) or not (
            self.minimum_text_characters
            <= len(text.strip())
            <= self.maximum_text_characters
        ):
            return self._json(
                start_response,
                "400 Bad Request",
                {"error": "Text must contain 100 to 20,000 characters."},
            )
        try:
            result = self.state.analyze(text)
        except AIDetectionError as exc:
            return self._json(
                start_response,
                "503 Service Unavailable",
                {"error": str(exc)},
            )
        except Exception:
            logger.exception("The dedicated Desklib request failed")
            return self._json(
                start_response,
                "500 Internal Server Error",
                {"error": "The inference service encountered an internal error."},
            )
        return self._json(start_response, "200 OK", {"result": result})

    def _authorized(self, environ):
        expected = f"Bearer {self.token}"
        supplied = environ.get("HTTP_AUTHORIZATION", "")
        return hmac.compare_digest(supplied.encode(), expected.encode())

    @staticmethod
    def _json(start_response, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode()
        start_response(
            status,
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
        return [body]
