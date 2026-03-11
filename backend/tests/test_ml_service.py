"""
Unit tests for :mod:`app.services.ml_service` and
:mod:`app.models.match_result`.

Tests are designed to work **without** a GPU or sentence-transformers
installed – the SBERT encoder is mocked where necessary.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.models.match_result import MatchResult, _grade
from app.services.ml_service import (
    MLService,
    W_KEYWORD,
    W_SEMANTIC,
    W_STRUCTURAL,
    W_TFIDF,
    _build_explanation,
    _detect_sections,
    _extract_skill_set,
    _structural_score,
)


# =====================================================================
# Fixtures
# =====================================================================

SAMPLE_RESUME = """
John Doe
john@example.com

SUMMARY
Experienced Python developer with 5 years of experience in machine learning
and cloud infrastructure.

SKILLS
Python, Flask, Django, AWS, Docker, Kubernetes, PostgreSQL, Git

EXPERIENCE
Senior Software Engineer at Acme Corp
January 2020 - Present
- Built REST APIs using Flask
- Deployed services on AWS EKS
- Implemented CI/CD pipelines

EDUCATION
Bachelor of Science in Computer Science from MIT, 2018

CERTIFICATIONS
AWS Certified Solutions Architect
"""

SAMPLE_JOB = """
Job Title: Senior Python Developer

Requirements:
- 5+ years of experience in Python
- Strong knowledge of Flask or Django
- Experience with AWS and cloud infrastructure
- Knowledge of Docker and Kubernetes
- Familiarity with PostgreSQL and Redis
- Experience with React or Angular front-end frameworks
- Machine learning experience preferred

Education:
Bachelor's degree in Computer Science or related field
"""

SHORT_RESUME = "Python developer AWS"
SHORT_JOB = "Need Python developer with AWS experience"


@pytest.fixture
def tmp_models(tmp_path):
    """Provide a temporary models directory."""
    return tmp_path / "models"


@pytest.fixture
def svc(tmp_models):
    """MLService with a temp models dir."""
    return MLService(models_dir=str(tmp_models))


# =====================================================================
# MatchResult dataclass
# =====================================================================

class TestMatchResult:
    def test_grade_a(self):
        r = MatchResult(score=95)
        assert r.grade == "A"
        assert r.score == 95.0

    def test_grade_b(self):
        assert MatchResult(score=80).grade == "B"

    def test_grade_c(self):
        assert MatchResult(score=65).grade == "C"

    def test_grade_d(self):
        assert MatchResult(score=55).grade == "D"

    def test_grade_f(self):
        assert MatchResult(score=20).grade == "F"

    def test_score_clamped_high(self):
        r = MatchResult(score=150)
        assert r.score == 100.0

    def test_score_clamped_low(self):
        r = MatchResult(score=-10)
        assert r.score == 0.0

    def test_to_dict_keys(self):
        r = MatchResult(score=72, matched_skills=["Python"])
        d = r.to_dict()
        assert set(d.keys()) == {
            "score", "grade", "matched_skills", "missing_skills",
            "subscores", "explanation",
            "candidate_name", "similarity_score", "ml_probability",
        }
        assert d["matched_skills"] == ["Python"]

    def test_grade_function(self):
        assert _grade(91) == "A"
        assert _grade(75) == "B"
        assert _grade(60) == "C"
        assert _grade(55) == "D"
        assert _grade(49) == "F"


# =====================================================================
# Skill extraction helpers
# =====================================================================

class TestSkillExtraction:
    def test_extracts_known_skills(self):
        skills = _extract_skill_set("I know Python, Flask, and AWS well.")
        assert "Python" in skills
        assert "Flask" in skills
        assert "AWS" in skills

    def test_no_false_positives(self):
        skills = _extract_skill_set("I enjoy long walks on the beach.")
        assert len(skills) == 0

    def test_empty_text(self):
        assert _extract_skill_set("") == set()

    def test_case_insensitive(self):
        skills = _extract_skill_set("experienced with DOCKER and kubernetes")
        assert "Docker" in skills
        assert "Kubernetes" in skills


# =====================================================================
# Structural detection
# =====================================================================

class TestStructural:
    def test_detects_sections(self):
        found = _detect_sections(SAMPLE_RESUME)
        assert "skills" in found
        assert "experience" in found
        assert "education" in found
        assert "certifications" in found

    def test_empty_text(self):
        assert _detect_sections("") == set()

    def test_score_range(self):
        s = _structural_score(SAMPLE_RESUME)
        assert 0.0 <= s <= 1.0
        assert s > 0.3  # at least a few sections present

    def test_no_sections(self):
        assert _structural_score("no headings here") == 0.0


# =====================================================================
# MLService initialisation
# =====================================================================

class TestMLServiceInit:
    def test_creates_models_dir(self, tmp_path):
        d = tmp_path / "new_models"
        svc = MLService(models_dir=str(d))
        assert d.exists()
        assert svc.is_ready

    def test_status_message(self, svc):
        assert "ready" in svc.status_message().lower()

    def test_check_status_keys(self, svc):
        status = svc.check_status()
        assert "tfidf_ready" in status
        assert "sbert_ready" in status
        assert "all_ready" in status


# =====================================================================
# TF-IDF vectorisation
# =====================================================================

class TestTfidfCosine:
    def test_identical_texts(self, svc):
        sim = svc._tfidf_cosine("python flask aws docker", "python flask aws docker")
        assert sim == pytest.approx(1.0, abs=0.01)

    def test_different_texts(self, svc):
        sim = svc._tfidf_cosine("python machine learning", "cooking baking recipes")
        assert sim < 0.3

    def test_empty_input(self, svc):
        sim = svc._tfidf_cosine("", "python")
        assert sim == pytest.approx(0.0, abs=0.01)


# =====================================================================
# SBERT cosine (mocked)
# =====================================================================

class TestSbertCosine:
    def test_high_similarity_mocked(self):
        vec = np.array([1.0, 0.0, 0.0])
        with patch("app.services.ml_service._get_sbert") as mock_get:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.stack([vec, vec])
            mock_get.return_value = mock_model
            sim = MLService._sbert_cosine("a", "a")
            assert sim == pytest.approx(1.0, abs=0.01)

    def test_orthogonal_vectors_mocked(self):
        with patch("app.services.ml_service._get_sbert") as mock_get:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ])
            mock_get.return_value = mock_model
            sim = MLService._sbert_cosine("a", "b")
            assert sim == pytest.approx(0.0, abs=0.01)

    def test_no_sbert_returns_zero(self):
        with patch("app.services.ml_service._get_sbert", return_value=None):
            sim = MLService._sbert_cosine("a", "b")
            assert sim == 0.0


# =====================================================================
# Keyword overlap
# =====================================================================

class TestKeywordOverlap:
    def test_full_overlap(self):
        ratio, matched, missing = MLService._keyword_overlap(
            "Python Flask AWS", "Python Flask AWS"
        )
        assert ratio == pytest.approx(1.0)
        assert "Python" in matched
        assert len(missing) == 0

    def test_partial_overlap(self):
        ratio, matched, missing = MLService._keyword_overlap(
            "Python Flask", "Python Flask AWS Docker"
        )
        assert 0 < ratio < 1
        assert "Python" in matched
        assert "AWS" in missing

    def test_no_overlap(self):
        ratio, matched, missing = MLService._keyword_overlap(
            "cooking baking", "Python AWS Docker"
        )
        assert ratio == 0.0
        assert len(matched) == 0
        assert len(missing) > 0

    def test_empty_job(self):
        ratio, matched, missing = MLService._keyword_overlap(
            "Python Flask", ""
        )
        # No JD skills → resume skills are "matched" by default
        assert ratio == 1.0
        assert len(missing) == 0


# =====================================================================
# Category subscores
# =====================================================================

class TestCategorySubscores:
    def test_education_met(self):
        sub = MLService._category_subscores(
            "Bachelor of Science in CS",
            "Bachelor's degree required",
            ["Python"], [],
        )
        assert sub["education"] == 100.0

    def test_education_underqualified(self):
        sub = MLService._category_subscores(
            "Associate degree in IT",
            "Master's degree required",
            [], [],
        )
        assert sub["education"] < 100.0

    def test_experience_years_met(self):
        sub = MLService._category_subscores(
            "10 years of experience",
            "5 years of experience required",
            [], [],
        )
        assert sub["experience"] == 100.0

    def test_experience_years_short(self):
        sub = MLService._category_subscores(
            "2 years of experience",
            "5 years of experience required",
            [], [],
        )
        assert sub["experience"] < 100.0

    def test_skills_subscore(self):
        sub = MLService._category_subscores(
            "Python Flask AWS",
            "Python Flask AWS Docker",
            ["Python", "Flask", "AWS"], ["Docker"],
        )
        assert sub["skills"] == pytest.approx(75.0, abs=0.1)


# =====================================================================
# Full scoring pipeline
# =====================================================================

class TestScoring:
    def _mock_sbert(self, sim_value: float):
        """Patch SBERT to return a fixed cosine similarity."""
        vec_a = np.array([1.0, 0.0])
        # Create vec_b such that cosine with vec_a = sim_value
        vec_b = np.array([sim_value, np.sqrt(1 - sim_value ** 2)])
        mock_model = MagicMock()
        mock_model.encode.return_value = np.stack([vec_a, vec_b])
        return patch("app.services.ml_service._get_sbert", return_value=mock_model)

    def test_good_match(self, svc):
        with self._mock_sbert(0.9):
            result = svc.score(SAMPLE_RESUME, SAMPLE_JOB)
        assert isinstance(result, MatchResult)
        assert result.score > 30
        assert result.grade in ("A", "B", "C", "D")
        assert len(result.matched_skills) > 0
        assert "semantic" in result.subscores
        assert "keyword" in result.subscores
        assert "tfidf" in result.subscores
        assert "structural" in result.subscores
        assert result.explanation

    def test_poor_match(self, svc):
        with self._mock_sbert(0.1):
            result = svc.score(
                "I am a chef with expertise in French cuisine and pastry arts",
                SAMPLE_JOB,
            )
        assert result.score < 40
        assert len(result.missing_skills) > 0

    def test_empty_resume(self, svc):
        result = svc.score("", SAMPLE_JOB)
        assert result.score == 0.0
        assert "empty" in result.explanation.lower()

    def test_empty_job(self, svc):
        result = svc.score(SAMPLE_RESUME, "")
        assert result.score == 0.0
        assert "empty" in result.explanation.lower()

    def test_subscores_present(self, svc):
        with self._mock_sbert(0.5):
            result = svc.score(SAMPLE_RESUME, SAMPLE_JOB)
        assert "skills" in result.subscores
        assert "experience" in result.subscores
        assert "education" in result.subscores

    def test_matched_skills_max_10(self, svc):
        with self._mock_sbert(0.5):
            result = svc.score(SAMPLE_RESUME, SAMPLE_JOB)
        assert len(result.matched_skills) <= 10

    def test_missing_skills_max_5(self, svc):
        with self._mock_sbert(0.5):
            result = svc.score(SAMPLE_RESUME, SAMPLE_JOB)
        assert len(result.missing_skills) <= 5

    def test_weights_sum_to_one(self):
        total = W_SEMANTIC + W_KEYWORD + W_TFIDF + W_STRUCTURAL
        assert total == pytest.approx(1.0)


# =====================================================================
# Batch scoring
# =====================================================================

class TestBatchScoring:
    def test_batch_returns_list(self, svc):
        with patch("app.services.ml_service._get_sbert", return_value=None):
            results = svc.batch_score(SAMPLE_RESUME, [SAMPLE_JOB, SAMPLE_JOB])
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, MatchResult) for r in results)

    def test_batch_empty_jobs(self, svc):
        results = svc.batch_score(SAMPLE_RESUME, [])
        assert results == []


# =====================================================================
# Model persistence (joblib)
# =====================================================================

class TestModelPersistence:
    def test_save_and_load_vectorizer(self, svc):
        # Fit a vectorizer first
        svc._ensure_vectorizer(["python flask aws", "java spring boot"])
        path = svc.save_vectorizer(tag="v_test")
        assert path.exists()
        assert "v_test" in path.name

        # Load into a new instance
        svc2 = MLService(models_dir=str(svc.models_dir))
        svc2.load_vectorizer(path)
        assert svc2.vectorizer is not None
        assert hasattr(svc2.vectorizer, "vocabulary_")

    def test_save_raises_without_vectorizer(self, svc):
        svc.vectorizer = None
        with pytest.raises(RuntimeError, match="No vectorizer"):
            svc.save_vectorizer()

    def test_auto_load_versioned_file(self, tmp_path):
        d = tmp_path / "m2"
        d.mkdir()
        svc = MLService(models_dir=str(d))
        svc._ensure_vectorizer(["hello world", "foo bar baz"])
        svc.save_vectorizer(tag="v20260101_000000")

        svc2 = MLService(models_dir=str(d))
        assert svc2.vectorizer is not None
        assert hasattr(svc2.vectorizer, "vocabulary_")


# =====================================================================
# Explanation builder
# =====================================================================

class TestExplanation:
    def test_contains_score(self):
        text = _build_explanation(
            75.0, "B", ["Python"], ["Docker"], {"semantic": 80, "keyword": 70, "tfidf": 60, "structural": 50}
        )
        assert "75.0" in text
        assert "Grade B" in text
        assert "Python" in text
        assert "Docker" in text

    def test_empty_lists(self):
        text = _build_explanation(30.0, "F", [], [], {"semantic": 20, "keyword": 10, "tfidf": 30, "structural": 5})
        assert "30.0" in text
        assert "Matched skills" not in text
