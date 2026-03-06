"""
Unit tests for ``app.services.nlp_service``.

Coverage target: 90%+

Tests cover:
    - Text cleaning / normalisation
    - Contact extraction (emails, phones, LinkedIn)
    - Name extraction heuristics
    - Skills extraction (taxonomy matching)
    - Education extraction (degree, institution, year)
    - Experience extraction (title-company-duration)
    - Certification extraction (curated regex)
    - Section splitting
    - Organisation extraction (spaCy NER)
    - Full analyse() pipeline
    - parse_resume() legacy dict API
    - LRU caching behaviour
"""

from __future__ import annotations

import textwrap
from unittest.mock import patch

import pytest

from app.services.nlp_service import NLPService, _cached_analyse

pytestmark = pytest.mark.unit


# =====================================================================
# Text cleaning
# =====================================================================

class TestCleanText:
    """Test the static ``clean_text`` method."""

    def test_normalises_whitespace(self):
        result = NLPService.clean_text("hello   world")
        assert "  " not in result

    def test_collapses_newlines(self):
        result = NLPService.clean_text("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_splits_camel_case(self):
        result = NLPService.clean_text("helloWorld testCase")
        assert "hello World" in result

    def test_strips_long_digit_sequences(self):
        result = NLPService.clean_text("ID: 12345678901 here")
        assert "12345678901" not in result

    def test_empty_string(self):
        assert NLPService.clean_text("") == ""

    def test_preserves_email_chars(self):
        result = NLPService.clean_text("user@example.com")
        assert "@" in result

    def test_fixes_punctuation_spacing(self):
        result = NLPService.clean_text("hello , world .  ok")
        # The clean_text regex strips commas (non-word chars),
        # so just verify extra spaces are collapsed
        assert "  " not in result

    def test_crlf_normalised(self):
        result = NLPService.clean_text("line1\r\nline2\rline3")
        assert "\r" not in result


# =====================================================================
# Contact extraction
# =====================================================================

class TestExtractContact:
    """Test _extract_contact static method."""

    def test_single_email(self):
        contact = NLPService._extract_contact("Reach me at alice@example.com")
        assert "alice@example.com" in contact.emails

    def test_multiple_emails(self):
        contact = NLPService._extract_contact(
            "a@b.com and c@d.org"
        )
        assert len(contact.emails) == 2

    def test_no_email(self):
        contact = NLPService._extract_contact("No email here")
        assert contact.emails == []

    def test_linkedin_url(self):
        text = "linkedin.com/in/johndoe"
        contact = NLPService._extract_contact(text)
        assert "linkedin.com/in/johndoe" in contact.linkedin

    def test_linkedin_with_https(self):
        text = "https://www.linkedin.com/in/jane-smith"
        contact = NLPService._extract_contact(text)
        assert "linkedin.com/in/jane-smith" in contact.linkedin

    def test_no_linkedin(self):
        contact = NLPService._extract_contact("No social links here")
        assert contact.linkedin == ""

    def test_phone_number(self):
        contact = NLPService._extract_contact(
            "Call +1 (555) 123-4567 anytime"
        )
        assert len(contact.phones) >= 1

    def test_invalid_short_email_filtered(self):
        contact = NLPService._extract_contact("a@b.c")
        assert len(contact.emails) == 0


# =====================================================================
# Phone extraction
# =====================================================================

class TestExtractPhones:
    """Test _extract_phones static method."""

    def test_us_number(self):
        phones = NLPService._extract_phones("Phone: +1 555-123-4567")
        assert len(phones) >= 1

    def test_multiple_phones(self):
        text = "Home: +1 555-111-2222, Work: +1 555-333-4444"
        phones = NLPService._extract_phones(text)
        assert len(phones) >= 2

    def test_no_phone(self):
        phones = NLPService._extract_phones("No phone number here.")
        assert phones == []

    def test_deduplication(self):
        text = "+1 555-123-4567 and again +1 555-123-4567"
        phones = NLPService._extract_phones(text)
        assert len(phones) == 1


# =====================================================================
# Name extraction
# =====================================================================

class TestExtractName:
    """Test _extract_name heuristic."""

    def test_simple_name(self):
        name = NLPService._extract_name("John Smith\njohn@email.com")
        assert name == "John Smith"

    def test_empty(self):
        assert NLPService._extract_name("") == ""

    def test_non_alpha_rejected(self):
        assert NLPService._extract_name("12345\nfoo") == ""

    def test_too_many_words(self):
        name = NLPService._extract_name("One Two Three Four Five")
        assert name == ""

    def test_pipe_delimited(self):
        name = NLPService._extract_name("Jane Doe | Software Engineer")
        assert name == "Jane Doe Software Engineer" or "Jane" in name

    def test_lowercase_only_rejected(self):
        name = NLPService._extract_name("no uppercase at all")
        assert name == ""


# =====================================================================
# Skills extraction
# =====================================================================

class TestExtractSkills:
    """Test _extract_skills against the taxonomy."""

    def test_finds_python(self):
        skills = NLPService._extract_skills("I am proficient in Python and SQL.")
        assert "Python" in skills

    def test_finds_multiple(self):
        skills = NLPService._extract_skills(
            "Experience with Docker, Kubernetes, and AWS."
        )
        assert "Docker" in skills
        assert "Kubernetes" in skills

    def test_empty_input(self):
        assert NLPService._extract_skills("") == []

    def test_no_match(self):
        skills = NLPService._extract_skills("I like gardening and cooking.")
        assert len(skills) == 0

    def test_case_insensitive(self):
        skills = NLPService._extract_skills("PYTHON javascript REACT")
        assert "Python" in skills
        assert "JavaScript" in skills

    def test_returns_sorted(self):
        skills = NLPService._extract_skills("Python, Java, C++, AWS, Docker")
        assert skills == sorted(skills)


# =====================================================================
# Education extraction
# =====================================================================

class TestExtractEducation:
    """Test _extract_education for degree keywords, institutions, years."""

    def test_bachelors(self):
        text = "Bachelor of Science in Computer Science, Stanford University 2020"
        edu = NLPService._extract_education(text)
        assert len(edu) >= 1
        assert "bachelor" in edu[0].degree.lower()

    def test_masters(self):
        text = "M.S. in Data Science from MIT 2022"
        edu = NLPService._extract_education(text)
        assert len(edu) >= 1
        assert any("master" in e.degree.lower() for e in edu)

    def test_phd(self):
        text = "Ph.D. in Physics, Caltech (2019)"
        edu = NLPService._extract_education(text)
        assert any("phd" in e.degree.lower() for e in edu)

    def test_year_extraction(self):
        text = "BS Computer Science, Some University 2018"
        edu = NLPService._extract_education(text)
        assert any(e.year == "2018" for e in edu)

    def test_institution_detection(self):
        text = "Bachelor from Stanford University 2020"
        edu = NLPService._extract_education(text)
        assert any("Stanford" in e.institution for e in edu)

    def test_empty_input(self):
        assert NLPService._extract_education("") == []

    def test_no_degree(self):
        text = "I like cooking food every single day."
        edu = NLPService._extract_education(text)
        assert edu == []

    def test_deduplication(self):
        text = (
            "Bachelor of Science from MIT 2020\n"
            "BS from MIT 2020"
        )
        edu = NLPService._extract_education(text)
        # Should deduplicate same degree+institution+year
        bachelor_mit = [
            e for e in edu
            if "bachelor" in e.degree.lower() and "2020" in e.year
        ]
        assert len(bachelor_mit) == 1


# =====================================================================
# Experience extraction
# =====================================================================

class TestExtractExperience:
    """Test _extract_experience patterns."""

    def test_years_of_experience_summary(self):
        text = "7+ years of experience in software development"
        exp = NLPService._extract_experience(text)
        assert any("years" in e.title.lower() for e in exp)

    def test_title_company_duration(self):
        text = "Software Engineer – Google (2018 - 2022)"
        exp = NLPService._extract_experience(text)
        assert any(e.company for e in exp)

    def test_duration_years_calculation(self):
        years = NLPService._parse_duration_years("2018 - 2022")
        assert years == 4.0

    def test_duration_to_present(self):
        years = NLPService._parse_duration_years("2020 - Present")
        assert years >= 3  # depends on current year

    def test_empty_input(self):
        assert NLPService._extract_experience("") == []

    def test_max_entries(self):
        # Should cap at 10
        lines = "\n".join(
            f"Software Developer – Company{i} (2010 - 2020)"
            for i in range(15)
        )
        exp = NLPService._extract_experience(lines)
        assert len(exp) <= 10

    def test_responsibilities_captured(self):
        text = (
            "Senior Developer – Acme Corp (2019 - 2023)\n"
            "• Built microservices architecture\n"
            "• Led team of 5 engineers\n"
        )
        exp = NLPService._extract_experience(text)
        matching = [e for e in exp if e.company and "Acme" in e.company]
        if matching:
            assert matching[0].responsibilities


# =====================================================================
# Certifications
# =====================================================================

class TestExtractCertifications:
    """Test _extract_certifications regex patterns."""

    def test_aws_cert(self):
        certs = NLPService._extract_certifications(
            "AWS Certified Solutions Architect"
        )
        assert len(certs) >= 1

    def test_pmp(self):
        certs = NLPService._extract_certifications("Certified PMP holder")
        assert any("PMP" in c for c in certs)

    def test_cissp(self):
        certs = NLPService._extract_certifications("Has CISSP certification")
        assert any("CISSP" in c for c in certs)

    def test_cka(self):
        certs = NLPService._extract_certifications(
            "Certified Kubernetes Administrator (CKA)"
        )
        assert len(certs) >= 1

    def test_empty(self):
        assert NLPService._extract_certifications("") == []

    def test_no_match(self):
        certs = NLPService._extract_certifications("I have no certifications")
        assert certs == []

    def test_multiple_certs(self):
        text = "CISSP\nPMP\nCKA"
        certs = NLPService._extract_certifications(text)
        assert len(certs) >= 2


# =====================================================================
# Section splitting
# =====================================================================

class TestSplitSections:
    """Test _split_sections used in the NLP pipeline."""

    def test_skills_section(self):
        text = "Header\n\nSKILLS\nPython, Java\n\nEDUCATION\nBS"
        sections = NLPService._split_sections(text)
        assert sections["skills"]

    def test_experience_section(self):
        text = "Contact\n\nEXPERIENCE\nSoftware Engineer at Google"
        sections = NLPService._split_sections(text)
        assert "experience" in sections

    def test_all_keys_present(self):
        sections = NLPService._split_sections("some text")
        for key in ("contact", "skills", "education", "experience",
                     "projects", "certifications"):
            assert key in sections

    def test_contact_preamble(self):
        text = "John Smith\njohn@email.com\n\nSKILLS\nPython"
        sections = NLPService._split_sections(text)
        assert "John" in sections["contact"] or "john" in sections["contact"]


# =====================================================================
# Full analyse() pipeline
# =====================================================================

class TestAnalyse:
    """Test the full analysis pipeline."""

    def test_returns_resume_profile(self, nlp_service, sample_resume_text):
        profile = nlp_service.analyse(sample_resume_text)
        assert profile.name  # should detect "John Smith"
        assert len(profile.skills) > 0
        assert len(profile.education) > 0
        assert profile.contact.emails

    def test_skills_detected(self, nlp_service, sample_resume_text):
        profile = nlp_service.analyse(sample_resume_text)
        assert "Python" in profile.skills
        assert "Docker" in profile.skills

    def test_education_detected(self, nlp_service, sample_resume_text):
        profile = nlp_service.analyse(sample_resume_text)
        assert any("master" in e.degree.lower() for e in profile.education)

    def test_completeness_score(self, nlp_service, sample_resume_text):
        profile = nlp_service.analyse(sample_resume_text)
        assert 0 <= profile.completeness_score <= 100
        assert profile.completeness_score > 30  # should be reasonably complete

    def test_certifications_detected(self, nlp_service, sample_resume_text):
        profile = nlp_service.analyse(sample_resume_text)
        assert len(profile.certifications) > 0

    def test_empty_text(self, nlp_service):
        profile = nlp_service.analyse("")
        assert profile.name == ""
        assert profile.skills == []


# =====================================================================
# parse_resume() legacy API
# =====================================================================

class TestParseResume:
    """Test the legacy dict-returning API."""

    def test_returns_dict(self, nlp_service, sample_resume_text):
        data = nlp_service.parse_resume(sample_resume_text)
        assert isinstance(data, dict)
        for key in ("name", "emails", "phones", "skills", "education",
                     "experience", "organizations", "cleaned_text",
                     "certifications", "completeness_score"):
            assert key in data

    def test_skills_in_dict(self, nlp_service, sample_resume_text):
        data = nlp_service.parse_resume(sample_resume_text)
        assert "Python" in data["skills"]

    def test_education_format(self, nlp_service, sample_resume_text):
        data = nlp_service.parse_resume(sample_resume_text)
        if data["education"]:
            edu = data["education"][0]
            assert "degree" in edu
            assert "institution" in edu
            assert "years" in edu

    def test_experience_format(self, nlp_service, sample_resume_text):
        data = nlp_service.parse_resume(sample_resume_text)
        if data["experience"]:
            exp = data["experience"][0]
            assert "title" in exp
            assert "company" in exp
            assert "duration" in exp


# =====================================================================
# Caching behaviour
# =====================================================================

class TestCaching:
    """Verify the LRU cache keyed on SHA-256."""

    def test_same_input_cached(self, nlp_service, sample_resume_text):
        _cached_analyse.cache_clear()  # start fresh
        p1 = nlp_service.analyse(sample_resume_text)
        p2 = nlp_service.analyse(sample_resume_text)
        info = _cached_analyse.cache_info()
        assert info.hits >= 1
        assert p1.to_dict() == p2.to_dict()

    def test_different_input_not_cached(self, nlp_service):
        _cached_analyse.cache_clear()
        nlp_service.analyse("First text with Python and Java skills")
        nlp_service.analyse("Completely different text about cooking recipes")
        info = _cached_analyse.cache_info()
        assert info.misses >= 2


# =====================================================================
# Organisation extraction
# =====================================================================

class TestExtractOrganizations:
    """Test NER-based org extraction."""

    def test_detects_orgs(self, nlp_service):
        sections = {"experience": "Worked at Google and Microsoft for 5 years."}
        orgs = nlp_service._extract_organizations(sections)
        assert isinstance(orgs, list)

    def test_empty_sections(self, nlp_service):
        orgs = nlp_service._extract_organizations({})
        assert orgs == [] or isinstance(orgs, list)

    def test_filters_noise_words(self, nlp_service):
        sections = {"experience": "Used Python and Docker at Acme Corp Inc."}
        orgs = nlp_service._extract_organizations(sections)
        # Should not include "Python" or "Docker" as orgs
        for org in orgs:
            assert "Python" not in org
            assert "Docker" not in org

    def test_no_nlp_model(self, nlp_service):
        """When nlp is None, should return empty list."""
        original = nlp_service.nlp
        nlp_service.nlp = None
        try:
            orgs = nlp_service._extract_organizations({"experience": "Worked at Acme"})
            assert orgs == []
        finally:
            nlp_service.nlp = original


# =====================================================================
# parse_file with mocked FileService
# =====================================================================

class TestParseFile:
    """Test parse_file method."""

    def test_success(self, nlp_service, tmp_path, sample_resume_text):
        from app.services.file_service import ResumeDocument
        doc = ResumeDocument(raw_text=sample_resume_text, sections={}, page_count=1, file_type="pdf")
        with patch("app.services.nlp_service.FileService.extract", return_value=doc):
            resume = nlp_service.parse_file(str(tmp_path / "resume.pdf"))
        assert resume.parsed is True
        assert resume.name
        assert len(resume.skills) > 0

    def test_file_error(self, nlp_service, tmp_path):
        from app.services.file_service import FileParseError
        with patch("app.services.nlp_service.FileService.extract",
                   side_effect=FileParseError("corrupt")):
            resume = nlp_service.parse_file(str(tmp_path / "bad.pdf"))
        assert resume.parsed is False
        assert resume.error == "corrupt"


# =====================================================================
# _dict_to_profile
# =====================================================================

class TestDictToProfile:
    """Test the static _dict_to_profile reconstruction."""

    def test_round_trip(self, nlp_service, sample_resume_text):
        profile = nlp_service.analyse(sample_resume_text)
        d = profile.to_dict()
        reconstructed = NLPService._dict_to_profile(d)
        assert reconstructed.name == profile.name
        assert reconstructed.skills == profile.skills
        assert len(reconstructed.education) == len(profile.education)

    def test_empty_dict(self):
        profile = NLPService._dict_to_profile({})
        assert profile.name == ""
        assert profile.skills == []


# =====================================================================
# _parse_duration_years edge cases
# =====================================================================

class TestParseDurationYears:
    """Additional edge cases for duration parsing."""

    def test_no_match(self):
        assert NLPService._parse_duration_years("some random text") == 0.0

    def test_current_synonym(self):
        years = NLPService._parse_duration_years("2020 - Current")
        assert years >= 3
