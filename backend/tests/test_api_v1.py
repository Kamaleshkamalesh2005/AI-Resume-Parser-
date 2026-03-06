"""
Integration tests for the API v1 endpoints (``/api/v1/…``).

Uses the Flask test client; SBERT is mocked so tests are fast and
don't require a GPU / large model download.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app import create_app
from config import TestingConfig


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def _mock_sbert():
    """Module-scoped SBERT mock so the app factory doesn't try to download."""
    rng = np.random.RandomState(99)

    def _fake_encode(texts, **kwargs):
        return rng.randn(len(texts), 384).astype(np.float32)

    mock_model = MagicMock()
    mock_model.encode.side_effect = _fake_encode
    with patch("app.services.ml_service._get_sbert", return_value=mock_model):
        yield


@pytest.fixture(scope="module")
def app(_mock_sbert):
    """Create the Flask application once for the whole test module."""
    application = create_app(TestingConfig)
    application.config["TESTING"] = True
    yield application


@pytest.fixture(scope="module")
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def _cleanup_feedback():
    """Remove feedback files created during tests."""
    yield
    fb = Path("feedback")
    if fb.exists():
        shutil.rmtree(fb, ignore_errors=True)


# ── Helpers ──────────────────────────────────────────────────────────

RESUME = (
    "John Doe\njohn@example.com\n\nSUMMARY\n"
    "Experienced Python developer with 5 years of experience in machine learning.\n\n"
    "SKILLS\nPython, Flask, Django, AWS, Docker, Kubernetes, PostgreSQL, Git\n\n"
    "EXPERIENCE\nSenior Software Engineer at Acme Corp\n"
    "January 2020 - Present\n- Built REST APIs using Flask\n\n"
    "EDUCATION\nBachelor of Science in Computer Science from MIT, 2018\n\n"
    "CERTIFICATIONS\nAWS Certified Solutions Architect\n"
)

JOB = (
    "Job Title: Senior Python Developer\n\nRequirements:\n"
    "- 5+ years of experience in Python\n"
    "- Strong knowledge of Flask or Django\n"
    "- Experience with AWS and Docker\n"
    "- Bachelor's degree in Computer Science or related field\n"
    "- Knowledge of PostgreSQL and Redis\n"
    "- Experience with React or Angular front-end frameworks\n"
)

SHORT_TEXT = "too short"


def _json(resp) -> Dict[str, Any]:
    return json.loads(resp.data)


# =====================================================================
# POST /api/v1/match
# =====================================================================

class TestMatch:
    def test_happy_path(self, client):
        resp = client.post(
            "/api/v1/match",
            json={"resume_text": RESUME, "job_description": JOB},
        )
        assert resp.status_code == 200
        body = _json(resp)
        assert body["success"] is True
        assert "data" in body
        data = body["data"]
        assert "score" in data
        assert "grade" in data
        assert "matched_skills" in data
        assert "missing_skills" in data
        assert "subscores" in data
        assert "explanation" in data
        assert body["errors"] == []
        assert body["meta"]["latency_ms"] > 0

    def test_missing_resume_text(self, client):
        resp = client.post(
            "/api/v1/match",
            json={"job_description": JOB},
        )
        assert resp.status_code == 422

    def test_missing_job_description(self, client):
        resp = client.post(
            "/api/v1/match",
            json={"resume_text": RESUME},
        )
        assert resp.status_code == 422

    def test_resume_too_short(self, client):
        resp = client.post(
            "/api/v1/match",
            json={"resume_text": SHORT_TEXT, "job_description": JOB},
        )
        assert resp.status_code == 422

    def test_job_too_short(self, client):
        resp = client.post(
            "/api/v1/match",
            json={"resume_text": RESUME, "job_description": SHORT_TEXT},
        )
        assert resp.status_code == 422

    def test_no_json_body(self, client):
        resp = client.post("/api/v1/match", data="not json")
        assert resp.status_code in (400, 422)

    def test_wrong_method(self, client):
        resp = client.get("/api/v1/match")
        assert resp.status_code == 405


# =====================================================================
# POST /api/v1/match/batch
# =====================================================================

class TestBatchMatch:
    def test_happy_path(self, client):
        resp = client.post(
            "/api/v1/match/batch",
            json={
                "resume_texts": [RESUME, RESUME],
                "job_description": JOB,
            },
        )
        assert resp.status_code == 200
        body = _json(resp)
        assert body["success"] is True
        data = body["data"]
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_pagination(self, client):
        resumes = [RESUME] * 5
        resp = client.post(
            "/api/v1/match/batch",
            json={
                "resume_texts": resumes,
                "job_description": JOB,
                "page": 2,
                "per_page": 2,
            },
        )
        assert resp.status_code == 200
        body = _json(resp)
        data = body["data"]
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["per_page"] == 2
        assert len(data["results"]) == 2

    def test_empty_resumes_list(self, client):
        resp = client.post(
            "/api/v1/match/batch",
            json={"resume_texts": [], "job_description": JOB},
        )
        assert resp.status_code == 422

    def test_missing_job_description(self, client):
        resp = client.post(
            "/api/v1/match/batch",
            json={"resume_texts": [RESUME]},
        )
        assert resp.status_code == 422

    def test_results_sorted_descending(self, client):
        resp = client.post(
            "/api/v1/match/batch",
            json={
                "resume_texts": [RESUME, RESUME],
                "job_description": JOB,
            },
        )
        body = _json(resp)
        scores = [r["score"] for r in body["data"]["results"]]
        assert scores == sorted(scores, reverse=True)


# =====================================================================
# GET /api/v1/health
# =====================================================================

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code in (200, 503)  # may be degraded in test env
        body = _json(resp)
        assert "data" in body
        assert "status" in body["data"]
        assert body["meta"]["latency_ms"] >= 0

    def test_health_components(self, client):
        resp = client.get("/api/v1/health")
        body = _json(resp)
        data = body["data"]
        assert "nlp_model" in data
        assert "ml_service" in data
        assert "storage" in data


# =====================================================================
# POST /api/v1/parse
# =====================================================================

class TestParse:
    def test_happy_path(self, client):
        resp = client.post(
            "/api/v1/parse",
            json={"resume_text": RESUME},
        )
        assert resp.status_code == 200
        body = _json(resp)
        assert body["success"] is True
        data = body["data"]
        assert "name" in data
        assert "contact" in data
        assert "skills" in data
        assert "education" in data
        assert "experience" in data
        assert "completeness_score" in data

    def test_text_too_short(self, client):
        resp = client.post(
            "/api/v1/parse",
            json={"resume_text": "short"},
        )
        assert resp.status_code == 422

    def test_missing_field(self, client):
        resp = client.post("/api/v1/parse", json={})
        assert resp.status_code == 422

    def test_extracts_skills(self, client):
        resp = client.post(
            "/api/v1/parse",
            json={"resume_text": RESUME},
        )
        body = _json(resp)
        skills = body["data"]["skills"]
        assert "Python" in skills
        assert "Flask" in skills


# =====================================================================
# GET /api/v1/skills
# =====================================================================

class TestSkills:
    def test_happy_path(self, client):
        resp = client.get("/api/v1/skills")
        assert resp.status_code == 200
        body = _json(resp)
        assert body["success"] is True
        data = body["data"]
        assert "skills" in data
        assert "total" in data
        assert data["total"] > 50

    def test_contains_known_skills(self, client):
        resp = client.get("/api/v1/skills")
        body = _json(resp)
        skills = body["data"]["skills"]
        assert "Python" in skills
        assert "AWS" in skills

    def test_latency_meta(self, client):
        resp = client.get("/api/v1/skills")
        body = _json(resp)
        assert body["meta"]["latency_ms"] >= 0


# =====================================================================
# POST /api/v1/feedback
# =====================================================================

class TestFeedback:
    def test_happy_path(self, client):
        resp = client.post(
            "/api/v1/feedback",
            json={
                "resume_text": RESUME,
                "job_description": JOB,
                "corrected_score": 85.0,
                "comment": "Match was underrated",
            },
        )
        assert resp.status_code == 201
        body = _json(resp)
        assert body["success"] is True
        assert "id" in body["data"]
        assert body["data"]["message"] == "Feedback recorded"

    def test_missing_corrected_score(self, client):
        resp = client.post(
            "/api/v1/feedback",
            json={"resume_text": RESUME, "job_description": JOB},
        )
        assert resp.status_code == 422

    def test_score_out_of_range(self, client):
        resp = client.post(
            "/api/v1/feedback",
            json={
                "resume_text": RESUME,
                "job_description": JOB,
                "corrected_score": 150,
            },
        )
        assert resp.status_code == 422

    def test_score_negative(self, client):
        resp = client.post(
            "/api/v1/feedback",
            json={
                "resume_text": RESUME,
                "job_description": JOB,
                "corrected_score": -5,
            },
        )
        assert resp.status_code == 422

    def test_optional_comment(self, client):
        resp = client.post(
            "/api/v1/feedback",
            json={
                "resume_text": RESUME,
                "job_description": JOB,
                "corrected_score": 50,
            },
        )
        assert resp.status_code == 201

    def test_feedback_file_created(self, client):
        client.post(
            "/api/v1/feedback",
            json={
                "resume_text": RESUME,
                "job_description": JOB,
                "corrected_score": 70,
            },
        )
        fb_dir = Path("feedback")
        assert fb_dir.exists()
        files = list(fb_dir.glob("fb_*.json"))
        assert len(files) >= 1
        content = json.loads(files[0].read_text(encoding="utf-8"))
        assert content["corrected_score"] == 70


# =====================================================================
# Response envelope format
# =====================================================================

class TestEnvelopeFormat:
    def test_envelope_keys_present(self, client):
        resp = client.get("/api/v1/skills")
        body = _json(resp)
        assert set(body.keys()) == {"success", "data", "errors", "meta"}

    def test_error_response_has_errors_list(self, client):
        resp = client.post("/api/v1/match", json={})
        body = _json(resp)
        # flask-smorest returns validation errors in its own format
        assert resp.status_code == 422
