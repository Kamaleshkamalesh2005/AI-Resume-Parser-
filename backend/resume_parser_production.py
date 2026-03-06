"""
Production-Grade Resume Parser  –  Strict Section-Aware Extraction

Architecture:
1. parse_sections()        – regex heading split, each section isolated
2. extract_contact_info()  – name / email / phone from header only
3. extract_skills()        – SKILLS section only
4. extract_education()     – EDUCATION section only (degree, institution, years)
5. extract_experience()    – EXPERIENCE section only (title, company, duration)
6. extract_organizations() – ORG NER restricted to EXPERIENCE + PROJECTS
7. clean_output()          – deduplicate, remove empty values
8. Debug logging for every step

Key guarantee:  education extraction NEVER reads experience text and vice-versa.
Organisation NER is never run on education text.
"""

import logging
import re
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

import spacy

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# MODULE-LEVEL CONSTANTS & COMPILED PATTERNS
# ============================================================================

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(
    r'(\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}|'
    r'\+\d{1,3}\s?\d{10,}|\d{10,}'
)
DURATION_PATTERN = re.compile(
    r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
    r'Dec(?:ember)?)\.?\s+\d{4}\s*[-–]\s*'
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
    r'Dec(?:ember)?|Present|Current)\.?\s*\d{0,4}',
    re.IGNORECASE,
)
YEAR_RANGE_PATTERN = re.compile(r'(20\d{2})\s*[-–]\s*(20\d{2}|Present|Current)', re.IGNORECASE)
SINGLE_YEAR_PATTERN = re.compile(r'\b(20\d{2})\b')

DEGREE_PATTERN = re.compile(
    r'\b(Bachelor|B\.?\s?Tech|B\.?E|B\.?S|B\.?A|B\.?Sc|B\.?Com|BCA|'
    r'Master|M\.?\s?Tech|M\.?E|M\.?S|M\.?A|M\.?Sc|M\.?Com|MCA|MBA|'
    r'Ph\.?D|Doctorate|Associate|Diploma)\b',
    re.IGNORECASE,
)

INSTITUTION_PATTERN = re.compile(
    r'(?:^|[,;\n]|\bat\b|\bfrom\b)\s*'
    r'([A-Z][A-Za-z\s&,\'\-]{3,60}?'
    r'(?:University|College|Institute(?:\s+of\s+[A-Za-z\s]+)?|School|Academy|Polytechnic|'
    r'Universit[aä]t|Universit[eé]|Hochschule|IIT|NIT|IIIT))\b'
)

# Section headings – order does not matter; we sort by position later
SECTION_HEADINGS = {
    'summary':        re.compile(r'^(?:PROFESSIONAL\s+)?(?:SUMMARY|OBJECTIVE|PROFILE)\s*:?\s*$', re.IGNORECASE),
    'education':      re.compile(r'^(?:EDUCATION|ACADEMIC\s+(?:BACKGROUND|QUALIFICATIONS?)|QUALIFICATIONS?)\s*:?\s*$', re.IGNORECASE),
    'skills':         re.compile(r'^(?:TECHNICAL\s+)?(?:SKILLS?|CORE\s+COMPETENCIES|TECHNICAL\s+EXPERTISE)\s*:?\s*$', re.IGNORECASE),
    'experience':     re.compile(r'^(?:WORK\s+)?(?:EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT(?:\s+HISTORY)?|INTERNSHIPS?|CAREER\s+HISTORY)\s*:?\s*$', re.IGNORECASE),
    'projects':       re.compile(r'^(?:PROJECTS?|PROJECT\s+EXPERIENCE|PERSONAL\s+PROJECTS?)\s*:?\s*$', re.IGNORECASE),
    'certifications': re.compile(r'^(?:CERTIFICATIONS?|LICENSES?|CREDENTIALS?|PROFESSIONAL\s+CERTIFICATIONS?|CERTIFICATES?|PROFESSIONAL\s+DEVELOPMENT)\s*:?\s*$', re.IGNORECASE),
}

# Job-title keywords for experience detection
JOB_TITLE_KEYWORDS = re.compile(
    r'\b(Intern|Developer|Engineer|Analyst|Manager|Architect|Director|Lead|'
    r'Specialist|Coordinator|Consultant|Associate|Designer|Administrator|'
    r'Scientist|Researcher|Officer|Head|Vice\s+President|VP|CTO|CEO|CFO|COO|'
    r'Senior|Junior|Trainee|Fellow)\b',
    re.IGNORECASE,
)

# Words that disqualify a spaCy ORG entity from being a real company
ORG_NOISE_WORDS = {
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby',
    'php', 'golang', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r',
    'matlab', 'sql', 'html', 'css', 'xml', 'json', 'yaml', 'bash',
    'shell', 'perl', 'lua', 'haskell', 'docker', 'aws', 'git', 'react',
    'kubernetes', 'experience', 'education', 'skills',
    # Degree / academic terms that should never be an org
    'artificial intelligence', 'machine learning', 'data science',
    'bachelor', 'master', 'phd', 'doctorate', 'diploma',
    'computer science', 'information technology',
    'nlp', 'natural language processing', 'deep learning',
    'rest', 'api', 'apis',
}

# Load spaCy model once at module level
try:
    NLP = spacy.load('en_core_web_sm')
except OSError:
    raise RuntimeError(
        "spaCy model 'en_core_web_sm' not found. "
        "Install with: python -m spacy download en_core_web_sm"
    )


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Education:
    """Education entry."""
    degree: str
    institution: str
    year_range: str = ""


@dataclass
class Experience:
    """Work experience entry."""
    title: str
    company: str
    duration: str = ""


@dataclass
class ResumeData:
    """Structured resume data."""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: List[str] = None
    education: List[Education] = None
    experience: List[Experience] = None
    organizations: List[str] = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.education is None:
            self.education = []
        if self.experience is None:
            self.experience = []
        if self.organizations is None:
            self.organizations = []

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'skills': self.skills,
            'education': [asdict(e) for e in self.education],
            'experience': [asdict(e) for e in self.experience],
            'organizations': self.organizations,
        }


# ============================================================================
# STEP 1 — SPLIT RESUME INTO SECTIONS
# ============================================================================

def parse_sections(text: str) -> Dict[str, str]:
    """Split *text* into named sections using heading detection.

    Everything between two headings belongs **only** to the upper heading.
    Content before the first heading is stored under ``"header"`` (contact area).

    Returns dict with keys: header, summary, education, skills, experience,
    projects, certifications.
    """
    sections: Dict[str, str] = {
        'header': '',
        'summary': '',
        'education': '',
        'skills': '',
        'experience': '',
        'projects': '',
        'certifications': '',
    }

    lines = text.split('\n')
    # Collect (line_index, section_key) for every detected heading
    boundaries: List[Tuple[int, str]] = []

    for idx, line in enumerate(lines):
        candidate = line.strip()
        if not candidate or len(candidate) > 80:
            continue
        for section_key, pattern in SECTION_HEADINGS.items():
            if pattern.match(candidate):
                boundaries.append((idx, section_key))
                break

    boundaries.sort(key=lambda b: b[0])

    logger.debug("Section boundaries detected: %s", boundaries)

    # Content before first heading → header (contact info)
    if boundaries:
        sections['header'] = '\n'.join(lines[:boundaries[0][0]]).strip()
    else:
        # No headings found – treat first 20% as header, rest as unknown
        cutoff = max(5, len(lines) // 5)
        sections['header'] = '\n'.join(lines[:cutoff]).strip()
        logger.warning("No section headings detected in resume text")
        return sections

    # Fill each section with text between its heading and the next heading
    for i, (start_idx, key) in enumerate(boundaries):
        content_start = start_idx + 1  # skip the heading line itself
        if i + 1 < len(boundaries):
            content_end = boundaries[i + 1][0]
        else:
            content_end = len(lines)
        section_text = '\n'.join(lines[content_start:content_end]).strip()
        sections[key] = section_text

    # Debug: log section lengths
    for key, val in sections.items():
        logger.debug("Section %-15s : %d chars", key, len(val))

    return sections


# ============================================================================
# STEP 2-helper — CONTACT EXTRACTION (from header only)
# ============================================================================

def extract_contact_info(text: str, header: str = "") -> Tuple[str, str, str]:
    """Extract name, email, phone from the header / top lines.

    *header* is the text above the first section heading.  If empty,
    falls back to the first 10 lines of *text*.
    """
    search_area = header if header.strip() else '\n'.join(text.split('\n')[:10])

    # Name: first line that is purely alphabetic words, max 4 words
    name = ""
    for line in search_area.split('\n'):
        clean = line.strip()
        if clean and re.match(r'^[a-zA-Z.\s]+$', clean):
            words = clean.split()
            if 1 <= len(words) <= 4:
                name = clean
                break

    email_match = EMAIL_PATTERN.search(search_area)
    email = email_match.group() if email_match else ""

    phone_match = PHONE_PATTERN.search(search_area)
    phone = phone_match.group().strip() if phone_match else ""

    return name, email, phone


# ============================================================================
# STEP 3 — SKILLS EXTRACTION (SKILLS section only)
# ============================================================================

def extract_skills(skills_section: str) -> List[str]:
    """Extract skills from the SKILLS section text only."""
    if not skills_section.strip():
        return []

    # Strip category labels like "Programming Languages:", "Databases:"
    category_re = (
        r'(?:Programming\s+Languages|Web\s+Development|Databases|'
        r'Tools\s*(?:&|and)\s*Platforms|Tools|Front.?End|Back.?End|'
        r'Mobile|Cloud|DevOps|Other\s+Skills|Frameworks|Libraries|'
        r'Operating\s+Systems|Software|Technologies)[\s:]*'
    )
    cleaned = re.sub(category_re, '', skills_section, flags=re.IGNORECASE)

    # Split on commas, pipes, bullets, semicolons, or newlines
    raw = re.split(r'[,|•;]\s*|\n+', cleaned)
    seen = set()
    skills = []
    for item in raw:
        s = item.strip().strip('-').strip()
        if s and len(s) > 1 and s.lower() not in seen:
            seen.add(s.lower())
            skills.append(s)
    return skills


# ============================================================================
# STEP 2 — EDUCATION EXTRACTION (EDUCATION section only)
# ============================================================================

def extract_education(education_section: str) -> List[Education]:
    """Extract education entries strictly from the EDUCATION section.

    Returns list of Education(degree, institution, year_range).
    Ignores numbers that are not plausible year ranges.
    """
    if not education_section.strip():
        return []

    educations: List[Education] = []
    seen: set = set()

    # Split into candidate entries by newlines, blank lines, or bullet markers
    # Each line or paragraph that contains a degree keyword is a separate entry
    entries = re.split(r'\n+', education_section)

    for entry in entries:
        entry = entry.strip()
        if not entry or len(entry) < 8:
            continue

        # Skip certification-only lines
        if re.search(r'\bcertification\b', entry, re.IGNORECASE):
            continue

        # --- Degree ---
        degree_match = DEGREE_PATTERN.search(entry)
        degree = degree_match.group(0).strip() if degree_match else ""

        # Expand degree with following context (e.g. "B.Tech in Computer Science")
        if degree_match:
            after = entry[degree_match.end():]
            field_match = re.match(r'\s*(?:in|of|–|-)\s+([A-Za-z\s&]+)', after)
            if field_match:
                degree = degree + " in " + field_match.group(1).strip()

        # --- Institution ---
        # Remove the degree portion first so the institution regex doesn't
        # swallow "Master in AI..., MIT University" as one token.
        inst_search_text = entry
        if degree_match:
            # Cut everything before the end of the degree+field match
            cut_end = degree_match.end()
            if degree_match:
                after = entry[degree_match.end():]
                field_m = re.match(r'\s*(?:in|of|–|-)\s+[A-Za-z\s&]+', after)
                if field_m:
                    cut_end = degree_match.end() + field_m.end()
            inst_search_text = entry[cut_end:]

        inst_match = INSTITUTION_PATTERN.search(inst_search_text)
        institution = inst_match.group(1).strip() if inst_match else ""

        # Fallback: line containing "at <Name>" or "from <Name>"
        if not institution:
            at_match = re.search(
                r'(?:at|from)\s+([A-Z][A-Za-z\s&,\'-]{3,50})', entry
            )
            if at_match:
                institution = at_match.group(1).strip()

        # --- Year range (only 20xx values, no random numbers) ---
        yr_match = YEAR_RANGE_PATTERN.search(entry)
        if yr_match:
            year_range = yr_match.group(0).strip()
        else:
            # Try to find a single year (graduation year)
            years = SINGLE_YEAR_PATTERN.findall(entry)
            year_range = years[0] if years else ""

        # Deduplicate
        key = (degree.lower(), institution.lower(), year_range)
        if key in seen:
            continue
        seen.add(key)

        if degree or institution:
            educations.append(Education(
                degree=degree,
                institution=institution,
                year_range=year_range,
            ))

    logger.debug("Education entries extracted: %d", len(educations))
    for ed in educations:
        logger.debug("  degree=%s  inst=%s  years=%s", ed.degree, ed.institution, ed.year_range)

    return educations


# ============================================================================
# STEP 3 — EXPERIENCE EXTRACTION (EXPERIENCE section only)
# ============================================================================

def extract_experience(experience_section: str) -> List[Experience]:
    """Extract work experience entries strictly from the EXPERIENCE section.

    Uses spaCy ORG NER for company detection and keyword matching for titles.
    """
    if not experience_section.strip():
        logger.debug("Experience section is empty — returning []")
        return []

    experiences: List[Experience] = []

    # Run spaCy on *only* this section
    doc = NLP(experience_section)

    # Collect ORG entities from this section
    org_entities = []
    for ent in doc.ents:
        if ent.label_ == 'ORG':
            org_name = ent.text.strip()
            if not _is_noise_org(org_name):
                org_entities.append((ent.start_char, org_name))

    # Split into candidate blocks by double newlines
    blocks = re.split(r'\n{2,}', experience_section)

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue

        lines = block.split('\n')
        first_line = lines[0].strip() if lines else ""

        # --- Try "Title - Company" or "Title at Company" on first line ---
        title = ""
        company = ""
        tc_match = re.match(
            r'^(.+?)\s*(?:[-–|@]|\bat\b)\s*(.+?)\s*$', first_line
        )
        if tc_match:
            candidate_title = tc_match.group(1).strip()
            candidate_company = tc_match.group(2).strip()
            # Verify the title side has a job keyword
            if JOB_TITLE_KEYWORDS.search(candidate_title):
                title = candidate_title
                company = candidate_company
            elif JOB_TITLE_KEYWORDS.search(candidate_company):
                # Reversed: Company - Title
                title = candidate_company
                company = candidate_title

        # --- Fallback: find job title keyword on any line ---
        if not title:
            for line in lines:
                if JOB_TITLE_KEYWORDS.search(line):
                    title = line.strip().rstrip(',;-–').strip()
                    break

        # --- Company fallback: first ORG entity in this block ---
        if not company:
            for _, org_name in org_entities:
                if org_name in block:
                    company = org_name
                    break

        # --- Duration ---
        dur_match = DURATION_PATTERN.search(block)
        if dur_match:
            duration = dur_match.group(0).strip()
        else:
            yr_match = YEAR_RANGE_PATTERN.search(block)
            duration = yr_match.group(0).strip() if yr_match else ""

        if title or company:
            experiences.append(Experience(
                title=title,
                company=company,
                duration=duration,
            ))

    logger.debug("Experience entries extracted: %d", len(experiences))
    for exp in experiences:
        logger.debug("  title=%s  company=%s  dur=%s", exp.title, exp.company, exp.duration)

    return experiences


# ============================================================================
# STEP 4 — ORGANIZATION FILTERING
# ============================================================================

def _is_noise_org(name: str) -> bool:
    """Return True if *name* is clearly not a real company."""
    low = name.lower()
    # Reject if any noise word appears in the entity
    for noise in ORG_NOISE_WORDS:
        if noise in low:
            return True
    # Reject very short (< 3 chars), single common words, or very long entities
    word_count = len(name.split())
    if len(name) < 3 or word_count > 6:
        return True
    return False


def extract_organizations(experience_text: str, projects_text: str) -> List[str]:
    """Extract real company / organisation names using spaCy NER.

    Runs NER **only** on the experience and projects sections — never on
    education or the full resume text.
    """
    combined = (experience_text + '\n' + projects_text).strip()
    if not combined:
        return []

    doc = NLP(combined)
    seen: set = set()
    orgs: List[str] = []

    for ent in doc.ents:
        if ent.label_ != 'ORG':
            continue
        org_name = ent.text.strip()
        if _is_noise_org(org_name):
            logger.debug("Filtered noise ORG: %s", org_name)
            continue
        if org_name not in seen:
            seen.add(org_name)
            orgs.append(org_name)

    logger.debug("Organisations extracted: %s", orgs)
    return orgs


# ============================================================================
# STEP 6 — CLEAN FINAL OUTPUT
# ============================================================================

def _clean_output(data: ResumeData) -> ResumeData:
    """Remove duplicates and empty values from final output."""
    # Deduplicate skills
    seen_skills: set = set()
    clean_skills = []
    for s in data.skills:
        if s and s.lower() not in seen_skills:
            seen_skills.add(s.lower())
            clean_skills.append(s)
    data.skills = clean_skills

    # Deduplicate education
    seen_edu: set = set()
    clean_edu = []
    for e in data.education:
        key = (e.degree.lower(), e.institution.lower())
        if key not in seen_edu and (e.degree or e.institution):
            seen_edu.add(key)
            clean_edu.append(e)
    data.education = clean_edu

    # Deduplicate experience
    seen_exp: set = set()
    clean_exp = []
    for x in data.experience:
        key = (x.title.lower(), x.company.lower())
        if key not in seen_exp and (x.title or x.company):
            seen_exp.add(key)
            clean_exp.append(x)
    data.experience = clean_exp

    # Deduplicate organizations
    seen_orgs: set = set()
    clean_orgs = []
    for o in data.organizations:
        if o and o.lower() not in seen_orgs:
            seen_orgs.add(o.lower())
            clean_orgs.append(o)
    data.organizations = clean_orgs

    return data


# ============================================================================
# MAIN PARSING FUNCTION
# ============================================================================

def parse_resume(text: str) -> ResumeData:
    """Parse resume with strict section-aware extraction.

    Guarantees:
    - Education extraction reads ONLY the education section.
    - Experience extraction reads ONLY the experience section.
    - Organisation NER runs ONLY on experience + projects sections.
    """
    if not text or not isinstance(text, str):
        raise ValueError("Resume text must be a non-empty string")

    # ── Step 1: Split into isolated sections ─────────────────────
    sections = parse_sections(text)

    logger.debug("=" * 60)
    logger.debug("RESUME PARSE — Section lengths:")
    for k, v in sections.items():
        logger.debug("  %-15s : %d chars", k, len(v))
    logger.debug("=" * 60)

    # ── Step 2: Contact info (header only) ───────────────────────
    name, email, phone = extract_contact_info(text, header=sections.get('header', ''))

    # ── Step 3: Skills (SKILLS section only) ─────────────────────
    skills = extract_skills(sections['skills'])

    # ── Step 4: Education (EDUCATION section only — never experience) ──
    education = extract_education(sections['education'])

    # ── Step 5: Experience (EXPERIENCE section only — never education) ──
    experience = extract_experience(sections['experience'])

    # ── Step 6: Organisations (experience + projects only) ───────
    organizations = extract_organizations(
        sections['experience'],
        sections['projects'],
    )

    # ── Step 7: Assemble & clean ─────────────────────────────────
    resume_data = ResumeData(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        education=education,
        experience=experience,
        organizations=organizations,
    )
    resume_data = _clean_output(resume_data)

    logger.debug("Final output: name=%s, email=%s, phone=%s", name, email, phone)
    logger.debug("  skills=%d  education=%d  experience=%d  orgs=%d",
                  len(resume_data.skills), len(resume_data.education),
                  len(resume_data.experience), len(resume_data.organizations))

    return resume_data


# ============================================================================
# CONVENIENCE FUNCTION FOR JSON OUTPUT
# ============================================================================

def parse_resume_json(text: str) -> Dict:
    """Parse resume and return as JSON-serializable dictionary."""
    return parse_resume(text).to_dict()
