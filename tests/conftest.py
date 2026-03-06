"""
Root-level conftest.py providing shared fixtures for tests/ directory.

These fixtures mirror those in backend/tests/conftest.py so that the
root-level copies of the unit tests (tests/unit/test_nlp_service.py etc.)
can run without needing the full Flask application context.
"""
from __future__ import annotations

import textwrap

import pytest


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
        Senior Software Engineer - Acme Corp (2020 - Present)
        - Designed microservices architecture serving 10M+ daily requests
        - Led migration from monolith to Kubernetes-based deployment
        - Implemented CI/CD pipeline reducing deployment time by 75%
        - Mentored team of 5 junior engineers

        Software Engineer - TechStart Inc (2017 - 2020)
        - Built RESTful APIs with Flask handling 50K requests/minute
        - Developed data pipelines using Apache Kafka and PostgreSQL
        - Contributed to open-source Python libraries (500+ GitHub stars)

        EDUCATION
        Master of Science in Computer Science
        Stanford University (2017)

        Bachelor of Science in Computer Engineering
        University of California, Berkeley (2015)

        CERTIFICATIONS
        AWS Certified Solutions Architect - Associate
        Certified Kubernetes Administrator (CKA)

        PROJECTS
        - Open-source resume parser using spaCy and machine learning
        - Real-time analytics dashboard with React and WebSockets
    """)


@pytest.fixture()
def nlp_service():
    """NLPService instance (uses real spaCy)."""
    from app.services.nlp_service import NLPService
    return NLPService()
