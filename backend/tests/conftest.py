"""
Shared pytest fixtures for the resume-matcher test suite.

Fixtures:
    app              – Flask test application
    client           – Flask test client (with JSON content-type)
    sample_resume_text – realistic multi-section resume string
    sample_jd_text     – software-engineer job description
    good_match_resume  – resume tailored to sample JD (high score)
    bad_match_resume   – irrelevant resume (low score)
    ml_service         – MLService with mocked SBERT
    nlp_service        – NLPService (spaCy loaded)
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Ensure backend/ is on sys.path so `from app.*` imports always resolve,
# regardless of how pytest is invoked (CI, IDE, command line).
# ---------------------------------------------------------------------------
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Flask app / client
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """Create a Flask test application."""
    os.environ.setdefault("FLASK_ENV", "testing")
    from config import TestingConfig
    from app import create_app

    application = create_app(config_class=TestingConfig)
    application.config["TESTING"] = True
    yield application


@pytest.fixture()
def client(app):
    """Flask test client."""
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Text fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_resume_text() -> str:
    """Realistic multi-section resume text."""
    return textwrap.dedent("""\
        John Smith
        john.smith@email.com | +1 (555) 123-4567
        linkedin.com/in/johnsmith

        SUMMARY
        Senior Software Engineer with 7+ years of experience building scalable
        web applications and distributed systems using Python, JavaScript,
        and cloud technologies.

        SKILLS
        Python, JavaScript, TypeScript, SQL, Java, Go
        Flask, Django, React, Node.js, Express
        AWS, Docker, Kubernetes, Terraform
        PostgreSQL, Redis, MongoDB, RabbitMQ
        CI/CD, Jenkins, GitHub Actions, Git
        Agile, Scrum, TDD, REST APIs

        EXPERIENCE
        Senior Software Engineer – Acme Corp (2020 - Present)
        • Designed microservices architecture serving 10M+ daily requests
        • Led migration from monolith to Kubernetes-based deployment
        • Implemented CI/CD pipeline reducing deployment time by 75%
        • Mentored team of 5 junior engineers

        Software Engineer – TechStart Inc (2017 - 2020)
        • Built RESTful APIs with Flask handling 50K requests/minute
        • Developed data pipelines using Apache Kafka and PostgreSQL
        • Contributed to open-source Python libraries (500+ GitHub stars)

        EDUCATION
        Master of Science in Computer Science
        Stanford University (2017)

        Bachelor of Science in Computer Engineering
        University of California, Berkeley (2015)

        CERTIFICATIONS
        AWS Certified Solutions Architect – Associate
        Certified Kubernetes Administrator (CKA)

        PROJECTS
        • Open-source resume parser using spaCy and machine learning
        • Real-time analytics dashboard with React and WebSockets
    """)


@pytest.fixture()
def sample_jd_text() -> str:
    """Job description from the fixtures directory."""
    return (FIXTURES_DIR / "sample_jd.txt").read_text(encoding="utf-8")


@pytest.fixture()
def good_match_resume() -> str:
    """Resume that closely matches the sample JD (expected high score)."""
    return textwrap.dedent("""\
        Jane Doe
        jane.doe@example.com | +1 (555) 987-6543
        linkedin.com/in/janedoe

        SUMMARY
        Senior Software Engineer with 6 years of experience in Python,
        JavaScript, and SQL. Extensive AWS and Docker expertise.

        SKILLS
        Python, JavaScript, SQL, Flask, Django, React
        AWS, Docker, Kubernetes, PostgreSQL, MySQL
        Redis, CI/CD, Jenkins, GitHub Actions
        Agile, Scrum, Git, REST APIs, TDD

        EXPERIENCE
        Senior Software Engineer – CloudCo (2019 - Present)
        • Built RESTful APIs with Flask serving 100K daily users
        • Deployed containerized microservices on AWS EKS (Kubernetes)
        • Implemented CI/CD pipelines with GitHub Actions
        • Mentored 3 junior developers in Python best practices

        Software Developer – DataFlow Inc (2017 - 2019)
        • Developed data processing pipelines in Python
        • Managed PostgreSQL and Redis infrastructure on AWS

        EDUCATION
        Master of Science in Computer Science
        MIT (2017)

        Bachelor of Science in Computer Science
        Georgia Tech (2015)

        CERTIFICATIONS
        AWS Certified Solutions Architect
    """)


@pytest.fixture()
def bad_match_resume() -> str:
    """Resume for a completely different field (expected low score)."""
    return textwrap.dedent("""\
        Maria Garcia
        maria.garcia@example.com

        SUMMARY
        Licensed clinical psychologist with 10 years of experience
        providing therapy and psychological assessments.

        SKILLS
        Cognitive Behavioral Therapy, Psychoanalysis
        Patient Assessment, Crisis Intervention
        HIPAA Compliance, Electronic Health Records

        EXPERIENCE
        Clinical Psychologist – Wellness Center (2014 - Present)
        • Conducted 30+ therapy sessions per week
        • Administered standardized psychological tests
        • Developed treatment plans for patients with anxiety disorders

        EDUCATION
        Doctor of Psychology (PsyD)
        Alliant International University (2014)
    """)


# ---------------------------------------------------------------------------
# Service fixtures
# ---------------------------------------------------------------------------

def _fake_sbert_encode(texts, **_kwargs):
    """Deterministic fake SBERT encoding for reproducible tests."""
    rng = np.random.RandomState(42)
    return rng.randn(len(texts), 384).astype(np.float32)


@pytest.fixture()
def ml_service(tmp_path):
    """MLService instance with SBERT mocked for speed."""
    import app.services.ml_service as ml_mod

    with patch.object(ml_mod, "_get_sbert") as mock_sbert:
        model = MagicMock()
        model.encode = _fake_sbert_encode
        mock_sbert.return_value = model

        from app.services.ml_service import MLService
        svc = MLService(models_dir=str(tmp_path))
        yield svc


@pytest.fixture()
def nlp_service():
    """NLPService instance (uses real spaCy)."""
    from app.services.nlp_service import NLPService
    return NLPService()
