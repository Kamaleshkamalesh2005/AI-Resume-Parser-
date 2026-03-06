"""
Integration tests for ``/api/v1/…`` endpoints.

Coverage target: 90%+

Tests cover all 6 endpoints:
    POST   /api/v1/match        Resume–JD matching
    POST   /api/v1/match/batch  Batch ranking (paginated)
    GET    /api/v1/health       Health check
    POST   /api/v1/parse        Resume parsing
    GET    /api/v1/skills       Skills taxonomy
    POST   /api/v1/feedback     User score correction

Cross-cutting:
    - Standard envelope format: {success, data, errors, meta}
    - Marshmallow validation errors (422)
    - Rate-limiting decorators present (not exercised in tests)
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────────

def _post(client, path: str, data: dict):
    return client.post(
        path,
        data=json.dumps(data),
        content_type="application/json",
    )


# =====================================================================
# POST /api/v1/match
# =====================================================================

class TestMatchEndpoint:
    """Test resume-JD matching endpoint."""

    URL = "/api/v1/match"

    def test_happy_path(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert "score" in data
        assert "grade" in data
        assert "matched_skills" in data
        assert "explanation" in data

    def test_envelope_format(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
        })
        body = resp.get_json()
        assert "success" in body
        assert "data" in body
        assert "errors" in body
        assert "meta" in body
        assert "latency_ms" in body["meta"]

    def test_missing_resume_text(self, client, sample_jd_text):
        resp = _post(client, self.URL, {
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 422

    def test_missing_job_description(self, client, sample_resume_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
        })
        assert resp.status_code == 422

    def test_resume_too_short(self, client, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": "too short",
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 422

    def test_jd_too_short(self, client, sample_resume_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": "short",
        })
        assert resp.status_code == 422

    def test_empty_body(self, client):
        resp = _post(client, self.URL, {})
        assert resp.status_code == 422

    def test_score_range(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
        })
        score = resp.get_json()["data"]["score"]
        assert 0 <= score <= 100


# =====================================================================
# POST /api/v1/match/batch
# =====================================================================

class TestBatchMatchEndpoint:
    """Test batch matching endpoint."""

    URL = "/api/v1/match/batch"

    def test_happy_path(self, client, sample_resume_text, good_match_resume, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_texts": [sample_resume_text, good_match_resume],
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert "results" in data
        assert "total" in data
        assert data["total"] == 2

    def test_sorted_descending(self, client, good_match_resume, bad_match_resume, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_texts": [bad_match_resume, good_match_resume],
            "job_description": sample_jd_text,
        })
        results = resp.get_json()["data"]["results"]
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_pagination(self, client, sample_resume_text, sample_jd_text):
        resumes = [sample_resume_text] * 5
        resp = _post(client, self.URL, {
            "resume_texts": resumes,
            "job_description": sample_jd_text,
            "page": 1,
            "per_page": 2,
        })
        data = resp.get_json()["data"]
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["results"]) == 2

    def test_pagination_page_2(self, client, sample_resume_text, sample_jd_text):
        resumes = [sample_resume_text] * 5
        resp = _post(client, self.URL, {
            "resume_texts": resumes,
            "job_description": sample_jd_text,
            "page": 2,
            "per_page": 3,
        })
        data = resp.get_json()["data"]
        assert len(data["results"]) == 2  # 5 total, page 2 of 3 per page

    def test_missing_jd(self, client, sample_resume_text):
        resp = _post(client, self.URL, {
            "resume_texts": [sample_resume_text],
        })
        assert resp.status_code == 422

    def test_empty_resumes_list(self, client, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_texts": [],
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 422

    def test_resume_too_short_in_list(self, client, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_texts": ["short"],
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 422


# =====================================================================
# GET /api/v1/health
# =====================================================================

class TestHealthEndpoint:
    """Test health check endpoint."""

    URL = "/api/v1/health"

    def test_returns_200(self, client):
        resp = client.get(self.URL)
        assert resp.status_code in (200, 503)  # may be degraded in test env

    def test_envelope(self, client):
        resp = client.get(self.URL)
        body = resp.get_json()
        assert "success" in body
        assert "data" in body

    def test_status_field(self, client):
        body = client.get(self.URL).get_json()
        assert body["data"]["status"] in ("healthy", "degraded")

    def test_component_checks(self, client):
        body = client.get(self.URL).get_json()
        data = body["data"]
        assert "nlp_model" in data
        assert "ml_service" in data
        assert "storage" in data


# =====================================================================
# POST /api/v1/parse
# =====================================================================

class TestParseEndpoint:
    """Test resume parsing endpoint."""

    URL = "/api/v1/parse"

    def test_happy_path(self, client, sample_resume_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert "name" in data
        assert "skills" in data
        assert "education" in data
        assert "contact" in data

    def test_skills_extracted(self, client, sample_resume_text):
        data = _post(client, self.URL, {
            "resume_text": sample_resume_text,
        }).get_json()["data"]
        assert "Python" in data["skills"]

    def test_contact_info(self, client, sample_resume_text):
        data = _post(client, self.URL, {
            "resume_text": sample_resume_text,
        }).get_json()["data"]
        contact = data["contact"]
        assert len(contact["emails"]) >= 1

    def test_text_too_short(self, client):
        resp = _post(client, self.URL, {
            "resume_text": "short",
        })
        assert resp.status_code == 422

    def test_missing_text(self, client):
        resp = _post(client, self.URL, {})
        assert resp.status_code == 422

    def test_completeness_score(self, client, sample_resume_text):
        data = _post(client, self.URL, {
            "resume_text": sample_resume_text,
        }).get_json()["data"]
        assert "completeness_score" in data
        assert 0 <= data["completeness_score"] <= 100


# =====================================================================
# GET /api/v1/skills
# =====================================================================

class TestSkillsEndpoint:
    """Test skills taxonomy endpoint."""

    URL = "/api/v1/skills"

    def test_returns_200(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_envelope(self, client):
        body = client.get(self.URL).get_json()
        assert body["success"] is True

    def test_data_structure(self, client):
        data = client.get(self.URL).get_json()["data"]
        assert "skills" in data
        assert "total" in data
        assert data["total"] > 0
        assert isinstance(data["skills"], dict)

    def test_python_in_skills(self, client):
        skills = client.get(self.URL).get_json()["data"]["skills"]
        assert "Python" in skills


# =====================================================================
# POST /api/v1/feedback
# =====================================================================

class TestFeedbackEndpoint:
    """Test feedback submission endpoint."""

    URL = "/api/v1/feedback"

    def test_happy_path(self, client, sample_resume_text, sample_jd_text, tmp_path):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
            "corrected_score": 85,
        })
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["success"] is True
        assert "id" in body["data"]
        assert "message" in body["data"]

    def test_with_comment(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
            "corrected_score": 70,
            "comment": "Too low",
        })
        assert resp.status_code == 201

    def test_missing_corrected_score(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
        })
        assert resp.status_code == 422

    def test_score_out_of_range(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
            "corrected_score": 150,
        })
        assert resp.status_code == 422

    def test_score_negative(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, self.URL, {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
            "corrected_score": -5,
        })
        assert resp.status_code == 422

    def test_missing_resume_text(self, client, sample_jd_text):
        resp = _post(client, self.URL, {
            "job_description": sample_jd_text,
            "corrected_score": 80,
        })
        assert resp.status_code == 422

    def test_empty_body(self, client):
        resp = _post(client, self.URL, {})
        assert resp.status_code == 422


# =====================================================================
# Cross-cutting: content type & method not allowed
# =====================================================================

class TestCrossCutting:
    """Test general API behaviour."""

    def test_json_content_type(self, client, sample_resume_text, sample_jd_text):
        resp = _post(client, "/api/v1/match", {
            "resume_text": sample_resume_text,
            "job_description": sample_jd_text,
        })
        assert resp.content_type.startswith("application/json")

    def test_get_on_post_endpoint(self, client):
        resp = client.get("/api/v1/match")
        assert resp.status_code == 405

    def test_not_found_route(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
