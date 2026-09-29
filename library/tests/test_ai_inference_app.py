"""Tests for the private Desklib WSGI service contract."""

import json
from io import BytesIO

from django.test import SimpleTestCase

from ai_inference.app import InferenceApplication


class StubState:
    status = "ready"

    def __init__(self):
        self.started = False
        self.received_text = ""

    def start(self):
        self.started = True

    def analyze(self, text):
        self.received_text = text
        return {
            "score": 61.0,
            "label": "Mixed / uncertain",
            "tone": "mixed",
            "ai_probability": 61.0,
            "human_probability": 39.0,
            "confidence": 61.0,
            "chunks_analyzed": 1,
            "detector_name": "Desklib Academic AI Text Detector",
            "model_name": "desklib/ai-text-detector-academic-v1.01",
            "model_version": "pinned-revision",
        }


class InferenceApplicationTests(SimpleTestCase):
    token = "inference-test-token-with-at-least-32-characters"

    def setUp(self):
        self.state = StubState()
        self.application = InferenceApplication(self.state, self.token)

    def request(self, method, path, payload=None, token=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
            "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        response_body = b"".join(self.application(environ, start_response))
        return captured["status"], json.loads(response_body)

    def test_health_reports_model_state_without_token(self):
        status, payload = self.request("GET", "/health")

        self.assertEqual(status, "200 OK")
        self.assertEqual(payload, {"status": "ready"})
        self.assertTrue(self.state.started)

    def test_analysis_requires_matching_token(self):
        status, payload = self.request(
            "POST",
            "/v1/analyze",
            {"text": "Academic evidence and context. " * 5},
            token="wrong-token",
        )

        self.assertEqual(status, "401 Unauthorized")
        self.assertEqual(payload, {"error": "Unauthorized."})

    def test_analysis_returns_only_detector_result(self):
        text = "Academic evidence and context should be reviewed carefully. " * 3

        status, payload = self.request(
            "POST",
            "/v1/analyze",
            {"text": text},
            token=self.token,
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["result"]["model_version"], "pinned-revision")
        self.assertEqual(self.state.received_text, text)

    def test_analysis_rejects_short_text(self):
        status, payload = self.request(
            "POST",
            "/v1/analyze",
            {"text": "too short"},
            token=self.token,
        )

        self.assertEqual(status, "400 Bad Request")
        self.assertIn("100 to 20,000", payload["error"])
