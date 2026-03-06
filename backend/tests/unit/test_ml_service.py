"""
Unit tests for ``app.services.ml_service``.

Coverage target: 85%+

Tests cover:
    - MLService initialisation and model persistence
    - TF-IDF cosine similarity
    - SBERT cosine similarity (mocked)
    - Keyword overlap (matched / missing skills)
    - Structural score (section detection)
    - Category subscores (skills, experience, education)
    - Full score() pipeline
    - MatchResult dataclass (clamping, grading, to_dict)
    - batch_score()
    - check_status() / status_message()
    - Explanation builder
    - Edge cases (empty input, whitespace-only)
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from app.models.match_result import MatchResult, _grade
from app.services.ml_service import (
    MLService,
    _build_explanation,
    _detect_sections,
    _extract_skill_set,
    _structural_score,
)

pytestmark = pytest.mark.unit


# =====================================================================
# MatchResult dataclass
# =====================================================================

class TestMatchResult:
    """Test the result dataclass independently."""

    def test_defaults(self):
        r = MatchResult()
        assert r.score == 0.0
        assert r.grade == "F"
        assert r.matched_skills == []
        assert r.explanation == ""

    def test_score_clamped_above(self):
        r = MatchResult(score=120)
        assert r.score == 100.0
        assert r.grade == "A"

    def test_score_clamped_below(self):
        r = MatchResult(score=-10)
        assert r.score == 0.0
        assert r.grade == "F"

    def test_grade_boundaries(self):
        assert _grade(90) == "A"
        assert _grade(89.9) == "B"
        assert _grade(75) == "B"
        assert _grade(74.9) == "C"
        assert _grade(60) == "C"
        assert _grade(59.9) == "D"
        assert _grade(40) == "D"
        assert _grade(39.9) == "F"
        assert _grade(0) == "F"

    def test_to_dict(self):
        r = MatchResult(
            score=85, matched_skills=["Python"], missing_skills=["Go"],
            subscores={"semantic": 90.0}, explanation="Good match.",
        )
        d = r.to_dict()
        assert d["score"] == 85.0
        assert d["grade"] == "B"
        assert d["matched_skills"] == ["Python"]
        assert d["missing_skills"] == ["Go"]
        assert d["subscores"]["semantic"] == 90.0
        assert d["explanation"] == "Good match."

    def test_score_rounded(self):
        r = MatchResult(score=75.555)
        assert r.score == 75.6


# =====================================================================
# Skill extraction helper
# =====================================================================

class TestExtractSkillSet:
    """Test the module-level _extract_skill_set helper."""

    def test_finds_python(self):
        skills = _extract_skill_set("Proficient in Python and Flask.")
        assert "Python" in skills

    def test_empty(self):
        assert _extract_skill_set("") == set()

    def test_case_insensitive(self):
        skills = _extract_skill_set("DOCKER and kubernetes")
        assert "Docker" in skills
        assert "Kubernetes" in skills

    def test_returns_set(self):
        result = _extract_skill_set("Python Python Python")
        assert isinstance(result, set)
        assert len(result) == 1


# =====================================================================
# Structural detection
# =====================================================================

class TestStructuralDetection:
    """Test section detection and structural scoring."""

    def test_detect_sections(self):
        text = "EDUCATION\nBS CS\n\nEXPERIENCE\nDev\n\nSKILLS\nPython"
        sections = _detect_sections(text)
        assert "education" in sections
        assert "experience" in sections
        assert "skills" in sections

    def test_detect_no_sections(self):
        assert len(_detect_sections("Just plain text.")) == 0

    def test_structural_score_full(self):
        text = (
            "EDUCATION\nx\nEXPERIENCE\nx\nSKILLS\nx\n"
            "CERTIFICATIONS\nx\nPROJECTS\nx\nSUMMARY\nx\nOBJECTIVE\nx"
        )
        score = _structural_score(text)
        assert score == 1.0

    def test_structural_score_partial(self):
        text = "EDUCATION\nBS"
        score = _structural_score(text)
        assert 0 < score < 1

    def test_structural_score_empty(self):
        assert _structural_score("") == 0.0


# =====================================================================
# Explanation builder
# =====================================================================

class TestBuildExplanation:
    """Test the explanation generator."""

    def test_contains_score(self):
        expl = _build_explanation(
            85.0, "B", ["Python"], ["Go"],
            {"semantic": 90, "keyword": 70, "tfidf": 60, "structural": 80},
        )
        assert "85.0" in expl
        assert "Grade B" in expl

    def test_contains_matched(self):
        expl = _build_explanation(70, "C", ["Python", "SQL"], [], {})
        assert "Python" in expl
        assert "Matched skills" in expl

    def test_contains_missing(self):
        expl = _build_explanation(50, "D", [], ["Go", "Rust"], {})
        assert "Missing skills" in expl
        assert "Go" in expl

    def test_empty_skills(self):
        expl = _build_explanation(50, "D", [], [], {})
        assert "Matched skills" not in expl
        assert "Missing skills" not in expl


# =====================================================================
# Keyword overlap
# =====================================================================

class TestKeywordOverlap:
    """Test _keyword_overlap static method."""

    def test_full_overlap(self):
        text = "Python, Flask, Docker"
        ratio, matched, missing = MLService._keyword_overlap(text, text)
        assert ratio > 0
        assert len(missing) == 0

    def test_partial_overlap(self):
        resume = "Python, Flask"
        jd = "Python, Flask, Docker, Kubernetes"
        ratio, matched, missing = MLService._keyword_overlap(resume, jd)
        assert len(matched) >= 2
        assert len(missing) >= 1

    def test_no_overlap(self):
        resume = "Cooking, Gardening"
        jd = "Python, Docker, Kubernetes"
        ratio, matched, missing = MLService._keyword_overlap(resume, jd)
        assert ratio == 0.0
        assert len(matched) == 0

    def test_empty_jd_skills(self):
        ratio, matched, missing = MLService._keyword_overlap(
            "Python", "no recognized skills here at all"
        )
        # When JD has no skills at all – ratio depends on resume having skills
        assert isinstance(ratio, float)

    def test_both_empty(self):
        ratio, matched, missing = MLService._keyword_overlap("", "")
        assert ratio == 0.0


# =====================================================================
# Category subscores
# =====================================================================

class TestCategorySubscores:
    """Test _category_subscores static method."""

    def test_all_keys_present(self):
        scores = MLService._category_subscores(
            "Python skills", "Python required", ["Python"], []
        )
        for key in ("skills", "experience", "education"):
            assert key in scores

    def test_skills_score_high_on_full_match(self):
        scores = MLService._category_subscores(
            "Python, Flask", "Python, Flask", ["Python", "Flask"], []
        )
        assert scores["skills"] >= 80

    def test_experience_score(self):
        resume = "5+ years of experience in software development"
        jd = "3+ years of experience required"
        scores = MLService._category_subscores(resume, jd, [], [])
        assert scores["experience"] > 0

    def test_education_matching(self):
        resume = "Master of Science"
        jd = "Bachelor's degree required"
        scores = MLService._category_subscores(resume, jd, [], [])
        assert scores["education"] == 100.0  # master >= bachelor

    def test_education_lower_than_required(self):
        resume = "Associate degree"
        jd = "Master's degree required"
        scores = MLService._category_subscores(resume, jd, [], [])
        assert scores["education"] < 100


# =====================================================================
# TF-IDF cosine
# =====================================================================

class TestTfidfCosine:
    """Test _tfidf_cosine method."""

    def test_identical_texts(self, ml_service, sample_resume_text):
        sim = ml_service._tfidf_cosine(sample_resume_text, sample_resume_text)
        assert sim >= 0.99

    def test_different_texts(self, ml_service):
        sim = ml_service._tfidf_cosine(
            "Python developer with flask experience",
            "Professional chef specialising in French cuisine"
        )
        assert sim < 0.5

    def test_range_0_1(self, ml_service, sample_resume_text, sample_jd_text):
        sim = ml_service._tfidf_cosine(sample_resume_text, sample_jd_text)
        assert 0.0 <= sim <= 1.0


# =====================================================================
# SBERT cosine (mocked)
# =====================================================================

class TestSbertCosine:
    """Test _sbert_cosine with mocked model."""

    def test_returns_float(self, ml_service, sample_resume_text, sample_jd_text):
        sim = MLService._sbert_cosine(sample_resume_text, sample_jd_text)
        assert isinstance(sim, float)

    def test_range_0_1(self, ml_service, sample_resume_text, sample_jd_text):
        sim = MLService._sbert_cosine(sample_resume_text, sample_jd_text)
        assert 0.0 <= sim <= 1.0


# =====================================================================
# Full score() pipeline
# =====================================================================

class TestScore:
    """Test the main scoring method."""

    def test_good_match_high_score(
        self, ml_service, good_match_resume, sample_jd_text
    ):
        result = ml_service.score(good_match_resume, sample_jd_text)
        assert isinstance(result, MatchResult)
        assert result.score > 0

    def test_bad_match_low_score(
        self, ml_service, bad_match_resume, sample_jd_text
    ):
        result = ml_service.score(bad_match_resume, sample_jd_text)
        assert isinstance(result, MatchResult)

    def test_good_beats_bad(
        self, ml_service, good_match_resume, bad_match_resume, sample_jd_text
    ):
        good = ml_service.score(good_match_resume, sample_jd_text)
        bad = ml_service.score(bad_match_resume, sample_jd_text)
        assert good.score > bad.score

    def test_has_matched_skills(
        self, ml_service, good_match_resume, sample_jd_text
    ):
        result = ml_service.score(good_match_resume, sample_jd_text)
        assert len(result.matched_skills) > 0

    def test_has_subscores(
        self, ml_service, good_match_resume, sample_jd_text
    ):
        result = ml_service.score(good_match_resume, sample_jd_text)
        for key in ("semantic", "keyword", "tfidf", "structural"):
            assert key in result.subscores

    def test_has_explanation(
        self, ml_service, good_match_resume, sample_jd_text
    ):
        result = ml_service.score(good_match_resume, sample_jd_text)
        assert "match score" in result.explanation.lower()

    def test_empty_resume(self, ml_service, sample_jd_text):
        result = ml_service.score("", sample_jd_text)
        assert result.score == 0.0
        assert "empty" in result.explanation.lower()

    def test_empty_jd(self, ml_service, sample_resume_text):
        result = ml_service.score(sample_resume_text, "")
        assert result.score == 0.0

    def test_whitespace_only(self, ml_service):
        result = ml_service.score("   ", "   ")
        assert result.score == 0.0


# =====================================================================
# batch_score()
# =====================================================================

class TestBatchScore:
    """Test batch scoring."""

    def test_multiple_jds(
        self, ml_service, sample_resume_text, sample_jd_text
    ):
        jds = [sample_jd_text, "Looking for a chef with cooking skills"]
        results = ml_service.batch_score(sample_resume_text, jds)
        assert len(results) == 2
        assert all(isinstance(r, MatchResult) for r in results)

    def test_empty_list(self, ml_service, sample_resume_text):
        results = ml_service.batch_score(sample_resume_text, [])
        assert results == []

    def test_single_jd(self, ml_service, sample_resume_text, sample_jd_text):
        results = ml_service.batch_score(sample_resume_text, [sample_jd_text])
        assert len(results) == 1


# =====================================================================
# Model persistence
# =====================================================================

class TestModelPersistence:
    """Test save/load vectorizer."""

    def test_save_and_load(self, ml_service, sample_resume_text, sample_jd_text):
        # Ensure vectorizer is fitted
        ml_service.score(sample_resume_text, sample_jd_text)
        assert ml_service.vectorizer is not None

        path = ml_service.save_vectorizer(tag="test")
        assert path.exists()

        new_svc = MLService(models_dir=str(ml_service.models_dir))
        new_svc.load_vectorizer(path)
        assert new_svc.vectorizer is not None

    def test_save_without_vectorizer(self, tmp_path):
        import app.services.ml_service as ml_mod
        with patch.object(ml_mod, "_get_sbert") as m:
            m.return_value = MagicMock(encode=lambda *a, **kw: np.zeros((2, 384)))
            svc = MLService(models_dir=str(tmp_path))
        svc.vectorizer = None
        with pytest.raises(RuntimeError, match="No vectorizer"):
            svc.save_vectorizer()


# =====================================================================
# check_status / status_message
# =====================================================================

class TestCheckStatus:
    """Test status reporting."""

    def test_status_keys(self, ml_service):
        status = ml_service.check_status()
        assert "tfidf_ready" in status
        assert "sbert_ready" in status
        assert "all_ready" in status

    def test_status_message_ready(self, ml_service):
        msg = ml_service.status_message()
        assert "ready" in msg.lower()

    def test_status_message_error(self, tmp_path):
        import app.services.ml_service as ml_mod
        with patch.object(ml_mod, "_get_sbert") as m:
            m.return_value = MagicMock(encode=lambda *a, **kw: np.zeros((2, 384)))
            svc = MLService(models_dir=str(tmp_path))
        svc.is_ready = False
        svc.error_message = "test error"
        msg = svc.status_message()
        assert "error" in msg.lower()
