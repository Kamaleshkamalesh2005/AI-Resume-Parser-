"""
ATS (Applicant Tracking System) simulation service.

Analyses a resume from the perspective of an automated ATS parser:

1. **Section headings** – checks for standard headings that ATS systems
   reliably detect (Education, Experience, Skills, etc.).
2. **Keyword density** – measures how thoroughly the resume echoes the
   terminology in the target job description.
3. **Formatting warnings** – flags constructs that commonly break ATS
   parsers (tables, columns, images, headers/footers, special chars).
4. **ATS-friendly rewrite** – rewrites bullet points to incorporate
   missing keywords from the job description.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Set, Tuple

from app.utils.skills_dict import SKILLS_DICT

# ── Standard ATS section headings ────────────────────────────────────
_ATS_HEADINGS: Dict[str, List[str]] = {
    "contact":        ["contact", "contact information", "personal information"],
    "summary":        ["summary", "professional summary", "profile", "objective",
                       "career objective", "about me"],
    "experience":     ["experience", "work experience", "professional experience",
                       "employment history", "work history"],
    "education":      ["education", "academic background", "qualifications"],
    "skills":         ["skills", "technical skills", "core competencies",
                       "key skills", "areas of expertise"],
    "certifications": ["certifications", "licenses", "credentials",
                       "professional certifications"],
    "projects":       ["projects", "key projects", "personal projects"],
}

# Minimum headings an ATS expects for a strong parse
_REQUIRED_HEADINGS = {"experience", "education", "skills"}

# ── Formatting anti-patterns ─────────────────────────────────────────
_FORMAT_PATTERNS: List[Tuple[str, str]] = [
    (r"<table[\s>]",          "HTML tables break ATS column parsing"),
    (r"\|.*\|.*\|",           "Pipe-delimited table/column layout detected"),
    (r"[┌┐└┘├┤┬┴┼─│═║╔╗╚╝]", "Box-drawing characters (table borders)"),
    (r"<img[\s>]",            "Embedded image tag (ATS cannot read images)"),
    (r"\.(png|jpg|jpeg|gif|svg|bmp)\b", "Image file reference"),
    (r"[\u2022\u25cf\u25cb\u25aa\u25ab\u2023\u27a4]",
                              "Fancy bullet characters – use plain - or *"),
    (r"[\u2018\u2019\u201c\u201d]",
                              "Smart/curly quotes – use straight quotes"),
    (r"\t{2,}",               "Multiple tabs used for alignment (use spaces)"),
    (r"={5,}|_{5,}|\*{5,}",  "Decorative line separators"),
    (r"(header|footer)\s*:",  "Header/footer markers (often stripped by ATS)"),
    (r"\\(textbf|textit|begin\{)",
                              "LaTeX formatting commands"),
]


# =====================================================================
# Public API
# =====================================================================

def ats_analyse(resume_text: str, job_text: str) -> Dict[str, Any]:
    """Run the full ATS simulation and return a result dict.

    Returns
    -------
    dict with keys:
        ats_score       : int   0-100 composite ATS-friendliness score
        section_score   : dict  heading analysis
        keyword_density : dict  keyword coverage stats
        format_warnings : list  formatting issues found
        rewritten_bullets : list  ATS-optimised bullet rewrites
    """
    sections   = _check_sections(resume_text)
    density    = _keyword_density(resume_text, job_text)
    warnings   = _format_warnings(resume_text)
    bullets    = _rewrite_bullets(resume_text, job_text)

    # Composite score: 30% sections + 40% keyword density + 30% formatting
    fmt_score = max(0, 100 - len(warnings) * 12)   # each warning costs 12 pts
    composite = round(
        0.30 * sections["score"]
        + 0.40 * density["score"]
        + 0.30 * fmt_score
    )
    composite = max(0, min(100, composite))

    return {
        "ats_score":          composite,
        "section_score":      sections,
        "keyword_density":    density,
        "format_warnings":    warnings,
        "rewritten_bullets":  bullets,
    }


# ── Section heading analysis ─────────────────────────────────────────

def _check_sections(text: str) -> Dict[str, Any]:
    """Score the use of standard ATS-parseable section headings."""
    text_lower = text.lower()
    found: Dict[str, bool] = {}

    for section, variants in _ATS_HEADINGS.items():
        found[section] = any(
            re.search(r"(?:^|\n)\s*" + re.escape(v) + r"\s*(?::|\n|$)", text_lower)
            for v in variants
        )

    present   = [s for s, ok in found.items() if ok]
    missing   = [s for s, ok in found.items() if not ok]
    required_present = _REQUIRED_HEADINGS & set(present)
    score = round(len(present) / len(_ATS_HEADINGS) * 100)

    return {
        "score":    score,
        "present":  sorted(present),
        "missing":  sorted(missing),
        "required_present": sorted(required_present),
        "required_missing": sorted(_REQUIRED_HEADINGS - required_present),
    }


# ── Keyword density analysis ────────────────────────────────────────

def _extract_jd_keywords(job_text: str) -> Set[str]:
    """Extract significant keywords from the job description."""
    keywords: Set[str] = set()

    # Skill-taxonomy matches
    text_lower = job_text.lower()
    for skill_name, tokens in SKILLS_DICT.items():
        for token in tokens:
            if re.search(r"\b" + re.escape(token) + r"\b", text_lower):
                keywords.add(skill_name.lower())
                break

    # Also extract meaningful bigrams/unigrams not in taxonomy
    _STOP = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "shall",
        "can", "not", "no", "nor", "so", "yet", "both", "either",
        "each", "every", "all", "any", "few", "more", "most", "other",
        "some", "such", "than", "too", "very", "just", "about", "above",
        "after", "again", "also", "as", "from", "into", "its", "it",
        "that", "this", "these", "those", "their", "our", "your", "we",
        "you", "they", "them", "us", "who", "what", "which", "when",
        "where", "how", "if", "then", "only", "own", "same", "up",
        "out", "off", "over", "under", "between", "through", "during",
        "before", "after", "while", "because", "since", "until",
    }
    words = re.findall(r"\b[a-z]{3,}\b", text_lower)
    for w in words:
        if w not in _STOP and len(w) > 3:
            keywords.add(w)

    return keywords


def _keyword_density(resume_text: str, job_text: str) -> Dict[str, Any]:
    """Measure how well the resume echoes JD keywords."""
    jd_keywords = _extract_jd_keywords(job_text)
    if not jd_keywords:
        return {"score": 100, "matched": [], "missing": [], "density_pct": 100.0}

    resume_lower = resume_text.lower()
    matched = sorted(k for k in jd_keywords
                     if re.search(r"\b" + re.escape(k) + r"\b", resume_lower))
    missing = sorted(jd_keywords - set(matched))

    density = len(matched) / len(jd_keywords) * 100
    score = round(min(density * 1.2, 100))    # slight boost, cap at 100

    return {
        "score":       score,
        "matched":     matched,
        "missing":     missing[:15],           # top 15 missing keywords
        "density_pct": round(density, 1),
    }


# ── Formatting warnings ─────────────────────────────────────────────

def _format_warnings(text: str) -> List[Dict[str, str]]:
    """Scan for formatting constructs that break ATS parsers."""
    warnings: List[Dict[str, str]] = []
    seen: set = set()

    for pattern, message in _FORMAT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and message not in seen:
            seen.add(message)
            warnings.append({
                "issue":   message,
                "snippet": text[max(0, match.start() - 10):match.end() + 10].strip(),
            })

    # Check for very long lines (ATS may truncate)
    for i, line in enumerate(text.split("\n"), 1):
        if len(line) > 200:
            msg = f"Line {i} exceeds 200 characters (may be truncated by ATS)"
            if msg not in seen:
                seen.add(msg)
                warnings.append({"issue": msg, "snippet": line[:60] + "…"})
            break  # report only the first long line

    return warnings


# ── ATS-friendly bullet rewrite ──────────────────────────────────────

def _rewrite_bullets(resume_text: str, job_text: str) -> List[Dict[str, str]]:
    """Rewrite resume bullet points to incorporate missing JD keywords.

    Only rewrites bullets that are *close* to a missing keyword's domain
    but don't yet mention it.  Returns up to 8 suggestions.
    """
    jd_skills: Set[str] = set()
    jd_lower = job_text.lower()
    for skill_name, tokens in SKILLS_DICT.items():
        for token in tokens:
            if re.search(r"\b" + re.escape(token) + r"\b", jd_lower):
                jd_skills.add(skill_name)
                break

    resume_lower = resume_text.lower()
    missing_skills = sorted(
        s for s in jd_skills
        if not re.search(r"\b" + re.escape(s.lower()) + r"\b", resume_lower)
    )

    if not missing_skills:
        return []

    # Extract bullet lines from resume
    bullet_re = re.compile(r"^[\s]*[-•*]\s+(.+)$", re.MULTILINE)
    bullets = bullet_re.findall(resume_text)

    if not bullets:
        return []

    rewrites: List[Dict[str, str]] = []

    for skill in missing_skills[:8]:
        # Find the most relevant existing bullet to enhance
        best_bullet = _find_related_bullet(skill, bullets)
        if best_bullet:
            enhanced = _enhance_bullet(best_bullet, skill)
            rewrites.append({
                "original":   best_bullet,
                "rewritten":  enhanced,
                "added_keyword": skill,
            })

    return rewrites


def _find_related_bullet(skill: str, bullets: List[str]) -> str | None:
    """Find the bullet most topically related to *skill*."""
    skill_lower = skill.lower()

    # Domain affinity mapping for smarter bullet selection
    _DOMAIN: Dict[str, List[str]] = {
        "aws":         ["cloud", "deploy", "infra", "server", "host", "scale"],
        "docker":      ["container", "deploy", "build", "image", "environment"],
        "kubernetes":  ["container", "orchestrat", "deploy", "cluster", "scale"],
        "python":      ["develop", "built", "implement", "script", "automat"],
        "flask":       ["api", "web", "backend", "endpoint", "server"],
        "django":      ["api", "web", "backend", "endpoint", "server"],
        "fastapi":     ["api", "web", "backend", "endpoint", "server"],
        "react":       ["frontend", "ui", "interface", "component", "web"],
        "javascript":  ["frontend", "web", "script", "develop", "built"],
        "typescript":  ["frontend", "web", "develop", "built", "type"],
        "postgresql":  ["database", "data", "query", "sql", "store"],
        "redis":       ["cache", "data", "queue", "store", "session"],
        "mongodb":     ["database", "data", "nosql", "store", "document"],
        "ci/cd":       ["pipeline", "deploy", "automat", "build", "test"],
        "terraform":   ["infra", "cloud", "deploy", "provision", "iac"],
        "machine learning": ["model", "data", "train", "predict", "algorithm"],
        "nlp":         ["text", "language", "process", "model", "data"],
        "git":         ["version", "code", "repository", "branch", "commit"],
        "sql":         ["database", "query", "data", "table", "store"],
        "rest api":    ["api", "endpoint", "http", "request", "service"],
        "microservices": ["service", "architect", "api", "deploy", "scale"],
    }

    hints = _DOMAIN.get(skill_lower, [])

    best_score = -1
    best_bullet = None
    for bullet in bullets:
        b_lower = bullet.lower()
        score = sum(1 for h in hints if h in b_lower)
        if score > best_score:
            best_score = score
            best_bullet = bullet

    # Fall back to the longest action-oriented bullet
    if best_score == 0:
        action_bullets = [b for b in bullets if re.match(
            r"(?:built|developed|designed|implemented|created|led|managed|"
            r"deployed|architected|migrated|optimized|automated)", b, re.I)]
        if action_bullets:
            best_bullet = max(action_bullets, key=len)
        elif bullets:
            best_bullet = max(bullets, key=len)

    return best_bullet


def _enhance_bullet(bullet: str, skill: str) -> str:
    """Append or integrate *skill* into *bullet* naturally."""
    # If bullet already ends with a technology list, append
    tech_list_re = re.compile(
        r"(.*(?:using|with|via|leveraging|in)\s+)([\w\s,/]+)$", re.IGNORECASE
    )
    m = tech_list_re.match(bullet.rstrip("."))
    if m:
        return f"{m.group(1)}{m.group(2)}, and {skill}."

    # Otherwise, append "using <skill>" or "leveraging <skill>"
    stripped = bullet.rstrip(".")
    return f"{stripped}, leveraging {skill}."
