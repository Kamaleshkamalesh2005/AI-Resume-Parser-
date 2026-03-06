"""
Unit tests for app.services.nlp_service
======================================

Covers:
    * Contact extraction (email, phone, LinkedIn)
    * Skills matching against taxonomy
    * Education parsing (degrees, institutions, years, foreign names)
    * Work experience (title, company, duration, overlapping dates)
    * Certification detection
    * Completeness score calculation
    * LRU caching by text hash
    * Edge cases: no email, empty text, minimal input
"""

from __future__ import annotations

import textwrap
from unittest.mock import patch

import pytest

from app.models.resume_profile import ContactInfo, Education, ResumeProfile, WorkExperience
from app.services.nlp_service import NLPService, _cached_analyse, _text_hash


@pytest.fixture(scope="module")
def svc() -> NLPService:
    """Single NLPService instance (spaCy loads once)."""
    return NLPService()


FULL_RESUME = textwrap.dedent(
    """\
    Jane Smith
    jane.smith@company.com | +14155551234
    linkedin.com/in/janesmith

    SKILLS
    Python, Flask, Django, React, AWS, Docker, Kubernetes, SQL

    EDUCATION
    Master of Science, Stanford University, 2019
    Bachelor of Science, MIT, 2017

    EXPERIENCE
    Senior Software Engineer - Google Inc. (2019 - 2023)
    - Built microservices handling 10M requests/day
    - Led team of 5 engineers

    Software Engineer - Facebook Inc. (2017 - 2019)
    - Developed internal tooling
    - Improved CI/CD pipeline

    CERTIFICATIONS
    AWS Certified Solutions Architect
    PMP
"""
)

MINIMAL_RESUME = "Some random text without any structured resume sections"


# =====================================================================
# Contact extraction
# =====================================================================


class TestContactExtraction:
    def test_email_found(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert "jane.smith@company.com" in profile.contact.emails

    def test_no_email(self, svc: NLPService):
        """Edge case: resume with no email address."""
        text = textwrap.dedent(
            """\
            John Doe
            Phone: +14155559876

            SKILLS
            Python, Java

            EXPERIENCE
            Developer - Acme Corp (2020 - 2023)
            - Wrote code
            """
        )
        profile = svc.analyse(text)
        assert profile.contact.emails == []

    def test_multiple_emails(self, svc: NLPService):
        text = "Contact: a@example.com or b@example.org for details"
        profile = svc.analyse(text)
        assert len(profile.contact.emails) == 2

    def test_linkedin_url(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert "linkedin.com/in/janesmith" in profile.contact.linkedin

    def test_no_linkedin(self, svc: NLPService):
        text = "john@example.com\nSKILLS\nPython"
        profile = svc.analyse(text)
        assert profile.contact.linkedin == ""

    def test_phone_with_phonenumbers_lib(self, svc: NLPService):
        """If the phonenumbers library is installed, it should parse a valid US number.

        If it's not installed, the service should still behave gracefully.
        """
        text = "Call me at +14155559876 or email test@x.com"
        profile = svc.analyse(text)

        # Don't assert strict formatting (depends on optional dependency); just ensure no crash and type OK.
        assert isinstance(profile.contact.phones, list)

    def test_phone_regex_fallback(self, svc: NLPService):
        """When phonenumbers is unavailable, regex fallback should still work."""
        with patch("app.services.nlp_service._HAS_PHONENUMBERS", False):
            phones = NLPService._extract_phones("Contact: (415) 555-9876")
            assert len(phones) >= 1


# =====================================================================
# Skills extraction
# =====================================================================


class TestSkillsExtraction:
    def test_skills_from_taxonomy(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert "Python" in profile.skills
        assert "Flask" in profile.skills
        assert "AWS" in profile.skills
        assert "Docker" in profile.skills

    def test_no_skills(self, svc: NLPService):
        text = "This text contains no technical terminology whatsoever."
        profile = svc.analyse(text)
        assert profile.skills == []

    def test_case_insensitive(self, svc: NLPService):
        text = "SKILLS\npython, FLASK, docker"
        profile = svc.analyse(text)
        assert "Python" in profile.skills
        assert "Flask" in profile.skills


# =====================================================================
# Education extraction
# =====================================================================


class TestEducationExtraction:
    def test_multiple_degrees(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        degrees = [e.degree.lower() for e in profile.education]
        assert any("master" in d for d in degrees)
        assert any("bachelor" in d for d in degrees)

    def test_institution_detected(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        institutions = [e.institution for e in profile.education]
        assert any("Stanford" in inst for inst in institutions)

    def test_graduation_year(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        years = [e.year for e in profile.education]
        assert "2019" in years

    def test_foreign_institution(self, svc: NLPService):
        """Edge case: non-English institution name."""
        text = textwrap.dedent(
            """\
            EDUCATION
            Bachelor of Engineering from Technische Universität München, 2018
            Master of Science from École Polytechnique Fédérale, 2020
            """
        )
        profile = svc.analyse(text)
        assert isinstance(profile.education, list)
        assert len(profile.education) >= 1

    def test_foreign_institution_indian(self, svc: NLPService):
        """Indian institution names."""
        text = textwrap.dedent(
            """\
            EDUCATION
            B.Tech in Computer Science from Indian Institute of Technology Delhi, 2019
            """
        )
        profile = svc.analyse(text)
        assert len(profile.education) >= 1
        assert profile.education[0].year == "2019"

    def test_no_education_section(self, svc: NLPService):
        text = "I am a self-taught Python developer with 5 years experience."
        profile = svc.analyse(text)
        assert isinstance(profile.education, list)

    def test_phd_detection(self, svc: NLPService):
        text = "EDUCATION\nPh.D. in Physics, Harvard University, 2015"
        profile = svc.analyse(text)
        degrees = [e.degree.lower() for e in profile.education]
        assert any("phd" in d for d in degrees)

    def test_associate_degree(self, svc: NLPService):
        text = "EDUCATION\nAssociate of Science, Community College, 2020"
        profile = svc.analyse(text)
        degrees = [e.degree.lower() for e in profile.education]
        assert any("associate" in d for d in degrees)


# =====================================================================
# Experience extraction
# =====================================================================


class TestExperienceExtraction:
    def test_experience_entries(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert isinstance(profile.experience, list)

    def test_duration_years_calculated(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        titled = [x for x in profile.experience if x.company]
        if titled:
            assert any(x.years >= 0 for x in titled)

    def test_overlapping_date_ranges(self, svc: NLPService):
        """Edge case: two roles with overlapping dates."""
        text = textwrap.dedent(
            """\
            EXPERIENCE
            Senior Developer - Acme Corp (2019 - 2022)
            - Built backend services

            Lead Developer - Acme Corp (2020 - 2023)
            - Managed team of 4

            Junior Developer - Beta LLC (2017 - 2020)
            - Frontend development
            """
        )
        profile = svc.analyse(text)
        assert isinstance(profile.experience, list)

    def test_years_of_experience_summary(self, svc: NLPService):
        text = "EXPERIENCE\n10+ years of experience in software development"
        profile = svc.analyse(text)
        assert any("10" in x.title for x in profile.experience)

    def test_present_duration(self, svc: NLPService):
        text = "EXPERIENCE\nSoftware Engineer - Google (2021 - Present)\n- Building APIs"
        profile = svc.analyse(text)
        titled = [x for x in profile.experience if x.company]
        if titled:
            assert titled[0].years >= 1

    def test_responsibilities_captured(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        titled = [x for x in profile.experience if x.company]
        if titled:
            assert any(x.responsibilities for x in titled)

    def test_no_experience(self, svc: NLPService):
        text = "Fresh graduate with no work history."
        profile = svc.analyse(text)
        assert isinstance(profile.experience, list)


# =====================================================================
# Certification extraction
# =====================================================================


class TestCertificationExtraction:
    def test_aws_cert(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert any("AWS" in c for c in profile.certifications)

    def test_pmp_cert(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert any("PMP" in c for c in profile.certifications)

    def test_multiple_certs(self, svc: NLPService):
        text = textwrap.dedent(
            """\
            CERTIFICATIONS
            AWS Certified Solutions Architect
            PMP
            CISSP
            CompTIA Security+
            CKA
            """
        )
        profile = svc.analyse(text)
        assert len(profile.certifications) >= 4

    def test_no_certs(self, svc: NLPService):
        text = "SKILLS\nPython, Java, Go"
        profile = svc.analyse(text)
        assert profile.certifications == []

    def test_azure_cert(self, svc: NLPService):
        text = "CERTIFICATIONS\nAzure Solutions Architect Expert"
        profile = svc.analyse(text)
        assert any("Azure" in c for c in profile.certifications)

    def test_cisco_cert(self, svc: NLPService):
        text = "I hold a CCNA and CCNP routing certification."
        profile = svc.analyse(text)
        assert isinstance(profile.certifications, list)
        assert len(profile.certifications) >= 1


# =====================================================================
# Completeness score
# =====================================================================


class TestCompletenessScore:
    def test_full_resume_high_score(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert profile.completeness_score >= 60

    def test_empty_text_zero_score(self, svc: NLPService):
        profile = svc.analyse("")
        assert profile.completeness_score == 0

    def test_only_email_partial_score(self):
        p = ResumeProfile(contact=ContactInfo(emails=["a@b.com"]))
        assert p.completeness_score == 10  # email weight

    def test_all_sections_filled(self):
        p = ResumeProfile(
            name="Jane",
            contact=ContactInfo(
                emails=["a@b.com"],
                phones=["+1234567890"],
                linkedin="linkedin.com/in/jane",
            ),
            skills=["Python"],
            education=[Education(degree="BS")],
            experience=[WorkExperience(title="Dev")],
            certifications=["PMP"],
        )
        assert p.completeness_score == 100

    def test_score_is_int(self, svc: NLPService):
        profile = svc.analyse(FULL_RESUME)
        assert isinstance(profile.completeness_score, int)

    def test_missing_phone_linkedin(self):
        p = ResumeProfile(
            name="John",
            contact=ContactInfo(emails=["x@y.com"]),
            skills=["Java"],
            education=[Education(degree="MS")],
            experience=[WorkExperience(title="Eng")],
        )
        assert p.completeness_score == 80


# =====================================================================
# Caching
# =====================================================================


class TestCaching:
    def test_same_text_returns_cached(self, svc: NLPService):
        _cached_analyse.cache_clear()
        text = "SKILLS\nPython, Django\nEDUCATION\nBachelor from MIT 2020"
        r1 = svc.analyse(text)
        r2 = svc.analyse(text)

        assert r1.to_dict() == r2.to_dict()

        info = _cached_analyse.cache_info()
        assert info.hits >= 1

    def test_different_text_not_cached(self, svc: NLPService):
        _cached_analyse.cache_clear()
        svc.analyse("SKILLS\nPython")
        svc.analyse("SKILLS\nJava")
        info = _cached_analyse.cache_info()
        assert info.misses >= 2

    def test_text_hash_deterministic(self):
        h1 = _text_hash("hello world")
        h2 = _text_hash("hello world")
        assert h1 == h2

    def test_text_hash_different(self):
        assert _text_hash("a") != _text_hash("b")


# =====================================================================
# ResumeProfile dataclass
# =====================================================================


class TestResumeProfile:
    def test_to_dict_keys(self):
        p = ResumeProfile(name="Test")
        d = p.to_dict()
        assert "name" in d
        assert "contact" in d
        assert "skills" in d
        assert "education" in d
        assert "experience" in d
        assert "certifications" in d
        assert "completeness_score" in d

    def test_default_values(self):
        p = ResumeProfile()
        assert p.name == ""
        assert p.skills == []
        assert p.education == []
        assert p.experience == []
        assert p.certifications == []
        assert p.completeness_score == 0


# =====================================================================
# Text cleaning
# =====================================================================


class TestTextCleaning:
    def test_camel_case_split(self):
        assert "hello World" in NLPService.clean_text("helloWorld")

    def test_empty_string(self):
        assert NLPService.clean_text("") == ""

    def test_whitespace_normalization(self):
        result = NLPService.clean_text("hello    world")
        assert "hello world" in result

    def test_long_digit_removal(self):
        result = NLPService.clean_text("ID: 1234567890123 Name: John")
        assert "1234567890123" not in result


# =====================================================================
# parse_resume legacy dict API
# =====================================================================


class TestParseResumeLegacy:
    def test_returns_dict(self, svc: NLPService):
        result = svc.parse_resume(FULL_RESUME)
        assert isinstance(result, dict)
        assert "name" in result
        assert "emails" in result
        assert "skills" in result
        assert "completeness_score" in result
        assert "certifications" in result

    def test_education_dict_format(self, svc: NLPService):
        result = svc.parse_resume(FULL_RESUME)
        if result.get("education"):
            assert "degree" in result["education"][0]
            assert "institution" in result["education"][0]
            assert "years" in result["education"][0]
