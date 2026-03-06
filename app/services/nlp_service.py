"""
NLP Service – resume text analysis, entity extraction, and structured parsing.

Uses spaCy (``en_core_web_md`` when available, falls back to ``en_core_web_sm``)
for NER and dependency parsing, the ``phonenumbers`` library for robust phone
extraction, and regex for emails, LinkedIn URLs, certifications, and dates.

Results are cached via ``functools.lru_cache`` keyed on the SHA-256 hash of
the input text.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import re
from typing import Any, Dict, List, Set, Tuple

import spacy

from app.models.resume import Resume
from app.models.resume_profile import (
    ContactInfo,
    Education,
    ResumeProfile,
    WorkExperience,
)
from app.services.file_service import FileParseError, FileService
from app.utils.skills_dict import SKILLS_DICT

logger = logging.getLogger(__name__)

# ── phone number parsing (optional graceful fallback) ────────────────
try:
    import phonenumbers as _pn

    _HAS_PHONENUMBERS = True
except ImportError:  # pragma: no cover
    _pn = None  # type: ignore[assignment]
    _HAS_PHONENUMBERS = False
    logger.warning("phonenumbers not installed – falling back to regex phone extraction")

# ── Degree keywords ──────────────────────────────────────────────────
DEGREE_KEYWORDS: Dict[str, List[str]] = {
    "bachelor": [
        "bachelors", "bachelor", "bs", "ba", "b.s.", "b.a.", "b.e.", "be",
        "b.tech", "btech", "b.sc", "bsc", "b.eng",
    ],
    "master": [
        "masters", "master", "ms", "ma", "m.s.", "m.a.", "mtech", "m.tech",
        "m.sc", "msc", "m.eng",
    ],
    "phd": ["phd", "ph.d.", "ph.d", "doctorate", "doctoral"],
    "mba": ["mba", "m.b.a."],
    "associate": ["associate", "a.s.", "a.a.", "aas"],
    "diploma": ["diploma", "postgraduate diploma", "pgd"],
}

# ── Certification patterns ───────────────────────────────────────────
_CERT_PATTERNS: List[str] = [
    # Cloud
    r"AWS\s+Certified[^\n]{0,60}",
    r"Azure\s+(?:Administrator|Developer|Solutions?\s+Architect|Data\s+Engineer|DevOps)[^\n]{0,40}",
    r"Google\s+Cloud\s+(?:Professional|Associate)[^\n]{0,40}",
    r"GCP\s+Certified[^\n]{0,40}",
    # Project Management
    r"PMP",
    r"PRINCE2",
    r"Certified\s+Scrum\s+Master",
    r"CSM",
    r"PMI[\-\s]ACP",
    r"CAPM",
    # Security
    r"CISSP",
    r"CISM",
    r"CEH",
    r"CompTIA\s+Security\+",
    r"CompTIA\s+Network\+",
    r"CompTIA\s+A\+",
    # Data / Analytics
    r"CPA",
    r"CFA",
    r"Certified\s+Data\s+(?:Scientist|Engineer|Analyst)",
    r"Tableau\s+(?:Desktop|Server)\s+(?:Specialist|Certified)",
    # Development
    r"Oracle\s+Certified[^\n]{0,40}",
    r"Cisco\s+(?:CCNA|CCNP|CCIE)[^\n]{0,30}",
    r"CCNA", r"CCNP", r"CCIE",
    r"Microsoft\s+Certified[^\n:]{0,40}",
    r"Certified\s+Kubernetes[^\n]{0,30}",
    r"CKA", r"CKAD",
    r"Terraform\s+(?:Associate|Professional)",
    r"ITIL",
    r"Six\s+Sigma[^\n]{0,20}",
    r"Salesforce[^\n]+Certified[^\n]{0,30}",
    r"SAFe\s+Agilist",
    r"TOGAF",
    r"RHCE", r"RHCSA",
]
_CERT_RE = re.compile(
    "|".join(f"(?:{p})" for p in _CERT_PATTERNS),
    re.IGNORECASE,
)

# ── Section heading patterns ─────────────────────────────────────────
_SECTION_PATTERNS: Dict[str, str] = {
    "skills": r"(?:^|\n)(TECHNICAL\s+SKILLS?|SKILLS?|CORE\s+COMPETENCIES)\s*(?::|\n|$)",
    "education": r"(?:^|\n)(EDUCATION|ACADEMIC\s+BACKGROUND|QUALIFICATIONS?)\s*(?::|\n|$)",
    "experience": (
        r"(?:^|\n)(PROFESSIONAL\s+EXPERIENCE|WORK\s+EXPERIENCE|EXPERIENCE|"
        r"EMPLOYMENT\s+HISTORY|INTERNSHIPS?|CAREER\s+HISTORY)\s*(?::|\n|$)"
    ),
    "projects": r"(?:^|\n)(PROJECTS?|PERSONAL\s+PROJECTS?)\s*(?::|\n|$)",
    "certifications": r"(?:^|\n)(CERTIFICATIONS?|CERTIFICATES?|PROFESSIONAL\s+DEVELOPMENT)\s*(?::|\n|$)",
}

# ── LinkedIn URL ─────────────────────────────────────────────────────
_LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?",
    re.IGNORECASE,
)

# ── Email ────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# =====================================================================
# Cache helpers
# =====================================================================

def _text_hash(text: str) -> str:
    """Return a hex SHA-256 digest for *text*."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


@functools.lru_cache(maxsize=256)
def _cached_analyse(text_hash: str, text: str) -> Dict[str, Any]:
    """Run the full analysis pipeline and cache by *text_hash*.

    Checks Redis first (if available), then falls back to the
    in-memory LRU cache.  Results are written back to Redis with
    a configurable TTL.
    """
    from app.cache import cache_get, cache_set

    cached = cache_get(text, prefix="nlp")
    if cached is not None:
        return cached

    svc = NLPService()
    profile = svc._analyse(text)
    result = profile.to_dict()

    cache_set(text, result, ttl=3600, prefix="nlp")
    return result


# =====================================================================
# NLPService
# =====================================================================

class NLPService:
    """Singleton-backed NLP service for resume analysis.

    The spaCy model is loaded once and shared across all instances.
    Analysis results are cached via an LRU cache keyed on the SHA-256
    hash of the input text.
    """

    _nlp: spacy.language.Language | None = None
    _model_name: str = ""

    def __init__(self) -> None:
        if NLPService._nlp is None:
            NLPService._load_spacy()
        self.nlp = NLPService._nlp

    @classmethod
    def _load_spacy(cls) -> None:
        """Load the spaCy model (idempotent)."""
        if cls._nlp is not None:
            return
        for model in ("en_core_web_md", "en_core_web_sm"):
            try:
                cls._nlp = spacy.load(model)
                cls._model_name = model
                logger.info("spaCy model loaded: %s", model)
                return
            except OSError:
                continue
        logger.error(
            "No spaCy model found – run: python -m spacy download en_core_web_md"
        )

    # ── public API ───────────────────────────────────────────────────

    def analyse(self, raw_text: str) -> ResumeProfile:
        """Analyse *raw_text* and return a :class:`ResumeProfile`.

        Results are cached by text hash.
        """
        h = _text_hash(raw_text)
        cached = _cached_analyse(h, raw_text)
        return self._dict_to_profile(cached)

    def parse_resume(self, raw_text: str) -> Dict[str, Any]:
        """Legacy dict-based API.  Delegates to :meth:`analyse`.

        Returns a dict compatible with the previous interface used by
        the API blueprint and :class:`Resume` model population.
        """
        profile = self.analyse(raw_text)
        return {
            "name": profile.name,
            "emails": profile.contact.emails,
            "phones": profile.contact.phones,
            "skills": profile.skills,
            "education": [
                {"degree": e.degree, "institution": e.institution, "years": e.year}
                for e in profile.education
            ],
            "experience": [
                {"title": x.title, "company": x.company, "duration": x.duration}
                for x in profile.experience
            ],
            "organizations": profile.organizations,
            "cleaned_text": profile.cleaned_text,
            "certifications": profile.certifications,
            "completeness_score": profile.completeness_score,
        }

    def parse_file(self, filepath: str) -> Resume:
        """Extract text from *filepath* and return a populated :class:`Resume`."""
        resume = Resume(filepath=filepath)
        try:
            doc = FileService.extract(filepath)
        except FileParseError as exc:
            resume.error = str(exc)
            return resume

        resume.raw_text = doc.raw_text
        data = self.parse_resume(doc.raw_text)

        resume.cleaned_text = data["cleaned_text"]
        resume.name = data["name"]
        resume.emails = data["emails"]
        resume.phones = data["phones"]
        resume.skills = data["skills"]
        resume.education = data["education"]
        resume.experience = data["experience"]
        resume.organizations = data["organizations"]
        resume.parsed = True
        resume.compute_features()
        return resume

    # ── internal pipeline ────────────────────────────────────────────

    def _analyse(self, raw_text: str) -> ResumeProfile:
        """Run every extraction step and build a :class:`ResumeProfile`.

        Strict section-aware extraction:
        - Education extraction reads ONLY the education section.
        - Experience extraction reads ONLY the experience section.
        - Organisation NER runs ONLY on experience + projects sections.
        """
        cleaned = self.clean_text(raw_text)
        sections = self._split_sections(cleaned)

        logger.debug("Section lengths: %s",
                      {k: len(v) for k, v in sections.items()})

        contact = self._extract_contact(cleaned)
        name = self._extract_name(sections.get("contact", ""))

        # Skills: prefer skills section, fall back to full text
        skills = self._extract_skills(sections.get("skills", "") or cleaned)

        # Education: ONLY from education section — never full text
        education = self._extract_education(sections.get("education", ""))

        # Experience: ONLY from experience section — never full text
        experience = self._extract_experience(sections.get("experience", ""))

        # Certifications: prefer section, fall back to full text
        certifications = self._extract_certifications(
            sections.get("certifications", "") or cleaned
        )

        # Organisations: ONLY from experience + projects sections
        orgs = self._extract_organizations(sections)

        from app.services.career_analyzer import analyse_career_timeline

        career_timeline = analyse_career_timeline(cleaned)

        logger.debug("Extracted: skills=%d education=%d experience=%d orgs=%d",
                      len(skills), len(education), len(experience), len(orgs))

        return ResumeProfile(
            name=name,
            contact=contact,
            skills=skills,
            education=education,
            experience=experience,
            certifications=certifications,
            organizations=orgs,
            cleaned_text=cleaned,
            career_timeline=career_timeline,
        )

    # ── text cleaning ────────────────────────────────────────────────

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalise whitespace, fix merged words, strip noise."""
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        # Separate camelCase merges from PDF extraction
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        # Strip long digit sequences (IDs, barcodes)
        text = re.sub(r"\d{7,}", "", text)
        # Fix punctuation spacing
        text = re.sub(r" +([,.])", r"\1", text)
        text = re.sub(r"([,.]) +", r"\1 ", text)
        # Keep only useful characters
        text = re.sub(r"[^\w\s.@:#\-/+()|\n]", "", text)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    # ── contact info ─────────────────────────────────────────────────

    @staticmethod
    def _extract_contact(text: str) -> ContactInfo:
        """Extract emails, phone numbers, and LinkedIn URL."""
        # Emails
        emails: List[str] = []
        for m in _EMAIL_RE.finditer(text):
            email = re.sub(r"^\d+", "", m.group()).strip()
            if email.count("@") == 1 and len(email) > 5:
                emails.append(email)
        emails = sorted(set(emails))

        # LinkedIn
        linkedin = ""
        li_match = _LINKEDIN_RE.search(text)
        if li_match:
            linkedin = li_match.group().rstrip("/")

        # Phone numbers
        phones = NLPService._extract_phones(text)

        return ContactInfo(emails=emails, phones=phones, linkedin=linkedin)

    @staticmethod
    def _extract_phones(text: str) -> List[str]:
        """Extract phone numbers using the *phonenumbers* library when
        available, otherwise fall back to regex.
        """
        phones: List[str] = []
        seen: Set[str] = set()

        if _HAS_PHONENUMBERS:
            for match in _pn.PhoneNumberMatcher(text, "US"):
                formatted = _pn.format_number(
                    match.number, _pn.PhoneNumberFormat.E164
                )
                if formatted not in seen:
                    phones.append(formatted)
                    seen.add(formatted)
            # Also try other regions if nothing found
            if not phones:
                for region in ("GB", "IN", "DE", "AU"):
                    for match in _pn.PhoneNumberMatcher(text, region):
                        formatted = _pn.format_number(
                            match.number, _pn.PhoneNumberFormat.E164
                        )
                        if formatted not in seen:
                            phones.append(formatted)
                            seen.add(formatted)
        else:
            # Regex fallback
            for m in re.finditer(
                r"(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
                text,
            ):
                digits = re.sub(r"[^\d]", "", m.group())
                if 10 <= len(digits) <= 15 and digits not in seen:
                    phones.append(m.group().strip())
                    seen.add(digits)

        return phones

    # ── section splitting ────────────────────────────────────────────

    @staticmethod
    def _split_sections(text: str) -> Dict[str, str]:
        """Split cleaned text into named sections.

        Content between two headings belongs ONLY to the upper heading.
        Content before the first heading is stored under ``contact``.
        """
        sections: Dict[str, str] = {
            k: "" for k in (
                "contact", "skills", "education", "experience",
                "projects", "certifications",
            )
        }
        boundaries: List[Tuple[int, str]] = []
        for name, pat in _SECTION_PATTERNS.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                boundaries.append((m.start(), name))
        boundaries.sort()

        if boundaries:
            sections["contact"] = text[: boundaries[0][0]].strip()
        else:
            sections["contact"] = text[: int(len(text) * 0.2)].strip()

        for i, (start, name) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            content = text[start:end].strip()
            first_nl = content.find("\n")
            if first_nl != -1:
                content = content[first_nl + 1:].strip()
            # Each section gets ONLY its own text — overwrite, never merge
            sections[name] = content

        logger.debug("Sections detected: %s",
                      {k: len(v) for k, v in sections.items() if v})
        return sections

    # ── name extraction ──────────────────────────────────────────────

    @staticmethod
    def _extract_name(contact_text: str) -> str:
        """Heuristic name detection from the contact/header section."""
        lines = [ln.strip() for ln in contact_text.split("\n") if ln.strip()]
        if not lines:
            return ""
        first = re.sub(r"[|•\-–—]", " ", lines[0]).strip()
        first = " ".join(first.split())
        if not re.match(r"^[A-Za-z\s.]+$", first):
            return ""
        if len(first.split()) > 4 or not any(c.isupper() for c in first):
            return ""
        return first

    # ── skills extraction ────────────────────────────────────────────

    @staticmethod
    def _extract_skills(text: str) -> List[str]:
        """Match text against the curated skills taxonomy."""
        if not text:
            return []
        text_lower = text.lower()
        found: Set[str] = set()
        for skill_name, tokens in SKILLS_DICT.items():
            for token in tokens:
                if re.search(r"\b" + re.escape(token) + r"\b", text_lower):
                    found.add(skill_name)
                    break
        return sorted(found)

    # ── education extraction ─────────────────────────────────────────

    @staticmethod
    def _extract_education(text: str) -> List[Education]:
        """Detect degrees, institutions, and graduation years.

        IMPORTANT: *text* must be ONLY the education section — never the
        full resume.  This prevents experience data from leaking into
        education results and vice-versa.
        """
        if not text:
            return []

        results: List[Education] = []
        seen: Set[Tuple[str, str, str]] = set()

        # Split into candidate entries — each line is a potential entry
        entries = re.split(r"\n+", text)

        for entry in entries:
            entry = entry.strip()
            if not entry or len(entry) < 8:
                continue
            # Skip certification-only lines
            if re.search(r"\bcertification\b", entry, re.IGNORECASE):
                continue

            # --- Degree ---
            degree_type = ""
            for dt, keywords in DEGREE_KEYWORDS.items():
                for kw in keywords:
                    if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", entry, re.IGNORECASE):
                        degree_type = dt.capitalize()
                        break
                if degree_type:
                    break

            # Expand with field of study — stop at commas, institution markers
            degree_label = degree_type
            if degree_type:
                dm = re.search(
                    r"(?:" + "|".join(
                        re.escape(k) for keys in DEGREE_KEYWORDS.values() for k in keys
                    ) + r")\s*(?:in|of)\s+([A-Za-z\s&]+?)"
                    r"(?=\s*,|\s+(?:from|at)\b|\s+[A-Z][a-z]+\s+(?:University|College|Institute|School|Academy)\b|\s*\d|$)",
                    entry,
                    re.IGNORECASE,
                )
                if dm:
                    field = dm.group(1).strip()
                    if field:
                        degree_label = degree_type + " in " + field

            # --- Institution ---
            inst = ""
            inst_m = re.search(
                r"(?:^|[\s,;(])([A-Z\u00C0-\u024F][\w\u00C0-\u024F\s']{2,50}?"
                r"(?:University|College|Institute|School|Academy|IIT|NIT|IIIT|"
                r"Universit[aä]t|Universit[eé]|Hochschule|"
                r"Politecnico|Universidade|Universidad|"
                r"Institut|Universiteit))\b",
                entry,
            )
            if inst_m:
                inst = re.sub(
                    r"^(?:at|in|from|of)\s+", "",
                    inst_m.group(1).strip(),
                    flags=re.IGNORECASE,
                )
            if not inst:
                of_m = re.search(
                    r"(?:from|at)\s+([A-Z\u00C0-\u024F][\w\u00C0-\u024F\s']{3,50})",
                    entry,
                )
                if of_m:
                    inst = of_m.group(1).strip()

            # --- Year (only 19xx/20xx, ignore other numbers) ---
            yr = ""
            yr_range = re.search(
                r"\b(19\d{2}|20\d{2})\s*[-\u2013]\s*(19\d{2}|20\d{2}|Present|Current)\b",
                entry, re.IGNORECASE,
            )
            if yr_range:
                yr = yr_range.group(0).strip()
            else:
                yr_single = re.search(r"\b(19\d{2}|20\d{2})\b", entry)
                if yr_single:
                    yr = yr_single.group(1)

            key = (degree_type.lower(), inst.lower(), yr)
            if key in seen:
                continue
            seen.add(key)

            if degree_label or inst:
                results.append(
                    Education(
                        degree=degree_label,
                        institution=inst,
                        year=yr,
                    )
                )
                logger.debug("  edu: degree=%s inst=%s yr=%s", degree_label, inst, yr)

        return results

    # ── experience extraction ────────────────────────────────────────

    _JOB_KEYWORDS: List[str] = [
        "intern", "developer", "engineer", "manager", "analyst",
        "architect", "director", "lead", "specialist", "coordinator",
        "consultant", "associate", "senior", "junior", "designer",
        "administrator", "scientist", "researcher", "officer", "head",
        "vice president", "vp", "cto", "ceo", "cfo", "coo",
    ]

    @staticmethod
    def _parse_duration_years(duration: str) -> float:
        """Estimate numeric years from a duration string like
        ``'2018 - 2021'`` or ``'2020 - Present'``.
        """
        m = re.search(r"(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|19\d{2})", duration)
        if m:
            return max(0, int(m.group(2)) - int(m.group(1)))
        m2 = re.search(r"(20\d{2}|19\d{2})\s*[-–]\s*(?:Present|Current)", duration, re.IGNORECASE)
        if m2:
            from datetime import date
            return max(0, date.today().year - int(m2.group(1)))
        return 0.0

    @staticmethod
    def _extract_experience(text: str) -> List[WorkExperience]:
        """Extract work-experience entries with title, company, duration,
        computed years, and a responsibilities summary.

        IMPORTANT: *text* must be ONLY the experience section — never
        the full resume.  This prevents education data from leaking
        into experience results.
        """
        if not text:
            return []

        results: List[WorkExperience] = []
        seen: Set[Tuple[str, str]] = set()

        # "X years of experience" summary
        ym = re.search(
            r"(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
            text,
            re.IGNORECASE,
        )
        if ym:
            yrs = float(ym.group(1))
            results.append(
                WorkExperience(
                    title=f"{ym.group(1)}+ years experience",
                    duration=f"{ym.group(1)} years",
                    years=yrs,
                )
            )

        # Split into blocks.  clean_text removes blank lines, so we
        # split at lines that look like new entry headers:
        # "Title – Company (Year - Year)" or start of a new role.
        _ENTRY_RE = re.compile(
            r"^[A-Z][\w\s]{3,50}[-–]\s*[A-Z][\w\s.&]*"
            r"\(?(?:19|20)\d{2}",
            re.MULTILINE,
        )
        split_positions = [m.start() for m in _ENTRY_RE.finditer(text)]
        if not split_positions:
            split_positions = [0]
        elif split_positions[0] != 0:
            split_positions.insert(0, 0)

        blocks = []
        for i, pos in enumerate(split_positions):
            end = split_positions[i + 1] if i + 1 < len(split_positions) else len(text)
            blocks.append(text[pos:end].strip())

        for block in blocks:
            block = block.strip()
            if not block or len(block) < 10:
                continue

            # Pattern: Title – Company (Duration)
            m = re.search(
                r"([A-Z][\w\s]{3,50}?)\s*[-–]\s*"
                r"([A-Z][\w\s.&]*?)\s*\(?\s*"
                r"((?:19|20)\d{2}\s*[-–]\s*(?:(?:19|20)\d{2}|Present|Current))",
                block,
                re.IGNORECASE,
            )
            if m:
                title = m.group(1).strip()[:60]
                company = m.group(2).strip()[:40]
                dur = m.group(3).strip()

                if not any(k in title.lower() for k in NLPService._JOB_KEYWORDS):
                    continue

                key = (title.lower(), company.lower())
                if key in seen:
                    continue
                seen.add(key)

                after = block[m.end(): m.end() + 300]
                resp_lines = [
                    ln.strip().lstrip("\u2022-\u2013*").strip()
                    for ln in after.split("\n")
                    if ln.strip() and not re.match(r"^[A-Z][\w\s]{5,50}[-\u2013]", ln)
                ]
                responsibilities = "; ".join(resp_lines[:3])

                results.append(
                    WorkExperience(
                        title=title,
                        company=company,
                        duration=dur,
                        years=NLPService._parse_duration_years(dur),
                        responsibilities=responsibilities[:200],
                    )
                )
                logger.debug("  exp: title=%s company=%s dur=%s", title, company, dur)
                continue

            # Fallback: detect job title keyword in block
            title = ""
            for line in block.split("\n"):
                if any(k in line.lower() for k in NLPService._JOB_KEYWORDS):
                    title = line.strip().rstrip(",;-\u2013").strip()[:60]
                    break
            if not title:
                continue

            # Try to find duration
            dur = ""
            dur_m = re.search(
                r"(?:19|20)\d{2}\s*[-–]\s*(?:(?:19|20)\d{2}|Present|Current)",
                block, re.IGNORECASE,
            )
            if dur_m:
                dur = dur_m.group(0).strip()

            key = (title.lower(), "")
            if key not in seen:
                seen.add(key)
                results.append(
                    WorkExperience(
                        title=title,
                        duration=dur,
                        years=NLPService._parse_duration_years(dur),
                    )
                )
                logger.debug("  exp (fallback): title=%s dur=%s", title, dur)

        return results[:10]

    # ── certification extraction ─────────────────────────────────────

    @staticmethod
    def _extract_certifications(text: str) -> List[str]:
        """Detect certification names via curated regex patterns."""
        if not text:
            return []
        found: Set[str] = set()
        for m in _CERT_RE.finditer(text):
            cert = m.group().strip()
            if cert and cert.lower() not in {c.lower() for c in found}:
                found.add(cert)
        return sorted(found)

    # ── organization extraction (NER) ────────────────────────────────

    # Words that disqualify a spaCy ORG entity from being a real company
    _ORG_NOISE: Set[str] = {
        "python", "java", "javascript", "typescript", "docker", "aws",
        "git", "react", "sql", "kubernetes", "experience", "education",
        "skills", "artificial intelligence", "machine learning",
        "data science", "bachelor", "master", "phd", "doctorate",
        "diploma", "computer science", "information technology",
        "nlp", "natural language processing", "deep learning",
        "rest", "api", "apis",
    }

    def _extract_organizations(self, sections: Dict[str, str]) -> List[str]:
        """Use spaCy NER to extract organisation names.

        Runs NER ONLY on experience + projects sections — never on
        education or the full resume text.
        """
        if not self.nlp:
            return []
        # Section isolation: experience + projects only
        relevant = (
            sections.get("experience", "")
            + "\n"
            + sections.get("projects", "")
        ).strip()
        if not relevant:
            return []

        doc = self.nlp(relevant)
        orgs: Set[str] = set()

        for ent in doc.ents:
            if ent.label_ != "ORG":
                continue
            t = ent.text.strip()
            words = t.split()
            if len(t) < 3 or len(words) > 6:
                continue
            # Filter noise entities
            low = t.lower()
            if any(noise in low for noise in self._ORG_NOISE):
                logger.debug("Filtered noise ORG: %s", t)
                continue
            if any(c.isupper() for c in t):
                orgs.add(t)

        logger.debug("Organisations extracted: %s", sorted(orgs))
        return sorted(orgs)

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _dict_to_profile(d: Dict[str, Any]) -> ResumeProfile:
        """Reconstruct a :class:`ResumeProfile` from a ``to_dict()`` output."""
        c = d.get("contact", {})
        return ResumeProfile(
            name=d.get("name", ""),
            contact=ContactInfo(
                emails=c.get("emails", []),
                phones=c.get("phones", []),
                linkedin=c.get("linkedin", ""),
            ),
            skills=d.get("skills", []),
            education=[
                Education(
                    degree=e.get("degree", ""),
                    institution=e.get("institution", ""),
                    year=e.get("year", ""),
                )
                for e in d.get("education", [])
            ],
            experience=[
                WorkExperience(
                    title=x.get("title", ""),
                    company=x.get("company", ""),
                    duration=x.get("duration", ""),
                    years=x.get("years", 0.0),
                    responsibilities=x.get("responsibilities", ""),
                )
                for x in d.get("experience", [])
            ],
            certifications=d.get("certifications", []),
            organizations=d.get("organizations", []),
            cleaned_text=d.get("cleaned_text", ""),
            career_timeline=d.get("career_timeline", {}),
        )

