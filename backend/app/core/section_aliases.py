"""
Section Heading Aliases for Universal Resume Parsing

Maps common heading variations to standard section categories.
Used with fuzzy matching to detect sections in different resume formats.
"""

SECTION_ALIASES = {
    "contact": [
        "contact", "contact info", "contact information", "personal details",
        "personal information", "header", "top"
    ],
    "education": [
        "education", "academic background", "academic qualification", 
        "qualifications", "academic", "schooling", "degree", "university",
        "colleges", "academic experience", "training", "certifications & education"
    ],
    "experience": [
        "work experience", "professional experience", "employment history",
        "experience", "prior experience", "professional background", 
        "work history", "career", "employment", "positions held",
        "professional summary", "work background"
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "technologies",
        "technical expertise", "expertise", "proficiencies", "abilities",
        "competencies", "key skills", "specialized skills", "technical background"
    ],
    "projects": [
        "projects", "key projects", "notable projects", "portfolio",
        "selected projects", "project experience", "work samples",
        "side projects", "open source", "github", "personal projects"
    ],
    "certifications": [
        "certifications", "licenses", "credentials", "certificates",
        "professional certifications", "accreditations", "awards",
        "honors", "memberships", "professional memberships"
    ],
    "summary": [
        "summary", "professional summary", "objective", "professional objective",
        "executive summary", "about", "about me", "profile", "professional profile"
    ]
}

# Fuzzy matching threshold (0-100, higher = stricter)
FUZZY_MATCH_THRESHOLD = 70

# Compiled patterns for quick matching
SECTION_HEADING_PATTERN = r"^[\s]*([a-zA-Z\s&/\-]+?)[\s]*(?:[:–—-])?[\s]*$"
