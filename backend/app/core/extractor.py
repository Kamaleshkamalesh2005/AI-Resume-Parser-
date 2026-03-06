"""
Universal Resume Parser - 9-Step Production Pipeline

Robust extraction pipeline supporting various resume formats:
- PDF (PyMuPDF)
- DOCX (python-docx)

Steps:
1. Text extraction and cleaning
2. Section detection with fuzzy matching
3. Contact information extraction
4. Skill extraction (no NER dependency)
5. Education extraction (section-isolated)
6. Experience extraction (section-isolated)
7. Organization filtering
8. Clean final output
9. Performance optimization
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except ImportError:
    NLP = None

from .skill_dict import SKILLS_LOWERCASE
from .section_aliases import SECTION_ALIASES, FUZZY_MATCH_THRESHOLD

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Education:
    """Education entry."""
    degree: str = ""
    institution: str = ""
    year_range: str = ""


@dataclass
class Experience:
    """Work experience entry."""
    job_title: str = ""
    company: str = ""
    duration: str = ""


@dataclass
class ResumeData:
    """Structured resume information."""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: List[str] = field(default_factory=list)
    education: List[Dict[str, str]] = field(default_factory=list)
    experience: List[Dict[str, str]] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    summary: str = ""


# ─────────────────────────────────────────────────────────────────────
# STEP 1: Text Extraction
# ─────────────────────────────────────────────────────────────────────

class TextExtractor:
    """Extract text from PDF and DOCX files."""

    @staticmethod
    def from_pdf(file_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        if not fitz:
            logger.warning("PyMuPDF not installed, skipping PDF extraction")
            return ""
        
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""

    @staticmethod
    def from_docx(file_path: str) -> str:
        """Extract text from DOCX using python-docx."""
        if not Document:
            logger.warning("python-docx not installed, skipping DOCX extraction")
            return ""
        
        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return ""

    @staticmethod
    def extract(file_path: str) -> str:
        """Extract text from file (auto-detect format)."""
        file_path = str(file_path).lower()
        
        if file_path.endswith('.pdf'):
            return TextExtractor.from_pdf(file_path)
        elif file_path.endswith('.docx'):
            return TextExtractor.from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace but PRESERVE NEWLINES for section detection
        text = re.sub(r'[ \t]+', ' ', text)  # Collapse spaces/tabs only
        text = re.sub(r'\n\s*\n+', '\n', text)  # Normalize multiple newlines to single
        
        # Fix broken lines (common in PDF extraction)
        text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        
        # Normalize encoding
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        
        return text.strip()


# ─────────────────────────────────────────────────────────────────────
# STEP 2: Section Detection
# ─────────────────────────────────────────────────────────────────────

class SectionDetector:
    """Detect resume sections using heading aliases and fuzzy matching."""

    @staticmethod
    def fuzzy_match(s1: str, s2: str, threshold: int = 70) -> bool:
        """Fuzzy string matching."""
        ratio = SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100
        return ratio >= threshold

    @staticmethod
    def detect_section(heading: str) -> Optional[str]:
        """Identify section type from heading text."""
        heading_clean = heading.lower().strip().replace(":", "").strip()
        
        for section_type, aliases in SECTION_ALIASES.items():
            for alias in aliases:
                if SectionDetector.fuzzy_match(heading_clean, alias, FUZZY_MATCH_THRESHOLD):
                    return section_type
        
        return None

    @staticmethod
    def detect_sections(text: str) -> Dict[str, str]:
        """Detect and isolate sections in resume text."""
        sections = {
            "contact": "",
            "education": "",
            "experience": "",
            "skills": "",
            "projects": "",
            "certifications": "",
            "summary": ""
        }
        
        lines = text.split('\n')
        current_section = "contact"  # First section is contact
        current_content = []
        
        for i, line in enumerate(lines):
            # Check if line is a section heading
            if line.strip() and re.match(r'^[A-Z][A-Za-z\s&/\-]*(?::)?$', line.strip()):
                detected = SectionDetector.detect_section(line)
                if detected:
                    # Save previous section
                    if current_content:
                        sections[current_section] += '\n'.join(current_content).strip() + '\n'
                    
                    current_section = detected
                    current_content = []
                    continue
            
            current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] += '\n'.join(current_content).strip()
        
        # Clean up empty sections
        return {k: v.strip() for k, v in sections.items() if v.strip()}


# ─────────────────────────────────────────────────────────────────────
# STEP 3: Contact Extraction
# ─────────────────────────────────────────────────────────────────────

class ContactExtractor:
    """Extract contact information from first 15 lines."""

    EMAIL_REGEX = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    PHONE_REGEX = re.compile(
        r'(?:\+\d{1,3}[\s-]?)?\(?[\s]?(\d{3})[\s-]?(\d{3})[\s-]?(\d{4})\b',
        re.IGNORECASE
    )

    @staticmethod
    def extract_email(text: str) -> str:
        """Extract email address."""
        match = ContactExtractor.EMAIL_REGEX.search(text)
        return match.group(0) if match else ""

    @staticmethod
    def extract_phones(text: str) -> List[str]:
        """Extract phone numbers."""
        matches = ContactExtractor.PHONE_REGEX.findall(text)
        return ['-'.join(m) for m in matches]

    @staticmethod
    def extract_name(text: str) -> str:
        """Extract name from first line containing 2-3 capitalized words."""
        lines = text.split('\n')[:15]
        
        for line in lines:
            tokens = line.strip().split()
            
            # Find sequences of 2-3 capitalized words
            if len(tokens) >= 2:
                capitalized = [t for t in tokens[:5] if t and t[0].isupper()]
                if 2 <= len(capitalized) <= 3:
                    return ' '.join(capitalized[:3])
        
        return ""

    @staticmethod
    def extract_contact(text: str) -> Tuple[str, str, List[str]]:
        """Extract all contact info."""
        first_lines = '\n'.join(text.split('\n')[:15])
        
        name = ContactExtractor.extract_name(first_lines)
        email = ContactExtractor.extract_email(first_lines)
        phones = ContactExtractor.extract_phones(first_lines)
        
        return name, email, phones


# ─────────────────────────────────────────────────────────────────────
# STEP 4: Skill Extraction
# ─────────────────────────────────────────────────────────────────────

class SkillExtractor:
    """Extract skills using predefined dictionary (no NER)."""

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract skills from text using dictionary matching."""
        skills = set()
        
        # Split into tokens
        tokens = re.findall(r'\b[\w\s\-/+#.]+\b', text, re.IGNORECASE)
        
        for token in tokens:
            token_lower = token.lower().strip()
            
            # Check exact match
            if token_lower in SKILLS_LOWERCASE:
                skills.add(SKILLS_LOWERCASE[token_lower])
            
            # Check partial matches for multi-word skills
            if ' ' in token_lower:
                for skill in SKILLS_LOWERCASE:
                    if skill in token_lower or token_lower in skill:
                        skills.add(SKILLS_LOWERCASE[skill])
        
        return sorted(list(skills))

    @staticmethod
    def deduplicate_skills(skills: List[str]) -> List[str]:
        """Remove duplicate skills."""
        return list(set(skills))


# ─────────────────────────────────────────────────────────────────────
# STEP 5: Education Extraction
# ─────────────────────────────────────────────────────────────────────

class EducationExtractor:
    """Extract education from EDUCATION section only."""

    DEGREE_KEYWORDS = {
        "bachelor": ["bachelor", "b.s.", "bs", "b.a.", "ba", "b.e.", "be", "b.tech", "btech"],
        "master": ["master", "m.s.", "ms", "m.a.", "ma", "m.tech", "mtech", "mba"],
        "phd": ["phd", "ph.d.", "doctorate"],
    }
    
    INSTITUTION_PATTERN = re.compile(
        r'(?:University|College|Institute|Academy|School|IIT|NIT)\b',
        re.IGNORECASE
    )
    
    YEAR_REGEX = re.compile(r'(19|20)\d{2}')

    @staticmethod
    def extract_degree(text: str) -> str:
        """Extract degree type."""
        text_lower = text.lower()
        
        for degree_type, keywords in EducationExtractor.DEGREE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return degree_type.capitalize()
        
        return ""

    @staticmethod
    def extract_institution(text: str) -> str:
        """Extract institution name."""
        match = EducationExtractor.INSTITUTION_PATTERN.search(text)
        if match:
            # Try to get full institution name
            start = max(0, match.start() - 50)
            snippet = text[start:match.end() + 50]
            
            # Extract capitalized sequence before institution keyword
            words = snippet.split()
            inst_words = []
            for word in words:
                if word and word[0].isupper():
                    inst_words.append(word)
                elif inst_words:
                    break
            
            return ' '.join(inst_words[-3:]) if inst_words else match.group(0)
        
        return ""

    @staticmethod
    def extract_year_range(text: str) -> str:
        """Extract year range."""
        years = EducationExtractor.YEAR_REGEX.findall(text)
        if years:
            return ' - '.join(set(years))
        return ""

    @staticmethod
    def extract_education(text: str) -> List[Dict[str, str]]:
        """Extract all education entries from education section."""
        if not text.strip():
            return []
        
        education_list = []
        
        # Split by double newline or numbered items
        entries = re.split(r'\n\s*\n|\n\s*(?=\d\.|\•|-|∑)', text)
        
        for entry in entries:
            if len(entry.strip()) < 10:
                continue
            
            degree = EducationExtractor.extract_degree(entry)
            institution = EducationExtractor.extract_institution(entry)
            year_range = EducationExtractor.extract_year_range(entry)
            
            if degree or institution:
                education_list.append({
                    "degree": degree,
                    "institution": institution,
                    "year_range": year_range
                })
        
        return education_list


# ─────────────────────────────────────────────────────────────────────
# STEP 6: Experience Extraction
# ─────────────────────────────────────────────────────────────────────

class ExperienceExtractor:
    """Extract experience from EXPERIENCE section only."""

    JOB_TITLE_KEYWORDS = [
        "intern", "engineer", "developer", "analyst", "scientist",
        "manager", "lead", "senior", "junior", "associate", "specialist",
        "architect", "consultant", "director", "coordinator", "officer"
    ]
    
    DURATION_REGEX = re.compile(
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*'
        r'(\d{4}|\d{1,2})\s*(?:–|[-–])\s*(?:Present|Current|\d{4}|\d{1,2})',
        re.IGNORECASE
    )

    @staticmethod
    def extract_job_title(text: str) -> str:
        """Extract job title from entry."""
        for keyword in ExperienceExtractor.JOB_TITLE_KEYWORDS:
            if keyword.lower() in text.lower():
                # Extract capitalized sequence
                pattern = rf'\b[A-Z][\w\s]+(?:{keyword})'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(0)
        
        return ""

    @staticmethod
    def extract_company(text: str) -> str:
        """Extract company name using spaCy ORG NER."""
        if not NLP:
            return ""
        
        try:
            doc = NLP(text[:500])  # Limit to first 500 chars for performance
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            
            # Filter out noise (future implementation)
            if orgs:
                return orgs[0]
        except Exception as e:
            logger.debug(f"spaCy NER failed: {e}")
        
        return ""

    @staticmethod
    def extract_duration(text: str) -> str:
        """Extract duration/date range."""
        match = ExperienceExtractor.DURATION_REGEX.search(text)
        return match.group(0) if match else ""

    @staticmethod
    def extract_experience(text: str) -> List[Dict[str, str]]:
        """Extract all experience entries from experience section."""
        if not text.strip():
            return []
        
        experience_list = []
        
        # Split by double newline or bullets
        entries = re.split(r'\n\s*\n|\n\s*(?=\d\.|\•|-|∑)', text)
        
        for entry in entries:
            if len(entry.strip()) < 10:
                continue
            
            job_title = ExperienceExtractor.extract_job_title(entry)
            company = ExperienceExtractor.extract_company(entry)
            duration = ExperienceExtractor.extract_duration(entry)
            
            if job_title or company:
                experience_list.append({
                    "job_title": job_title,
                    "company": company,
                    "duration": duration
                })
        
        return experience_list


# ─────────────────────────────────────────────────────────────────────
# STEP 7: Organization Filtering
# ─────────────────────────────────────────────────────────────────────

class OrganizationFilter:
    """Filter spaCy ORG entities for valid organizations."""

    NOISE_WORDS = {
        "python", "java", "javascript", "c++", "c#", "ruby", "go", "rust",
        "machine learning", "artificial intelligence", "ml", "ai", "deep learning",
        "bachelor", "master", "phd", "degree", "certificate", "certification",
        "django", "flask", "react", "angular", "vue", "spring", "nodejs",
        "sql", "mongodb", "postgresql", "docker", "kubernetes", "git", "github"
    }

    @staticmethod
    def is_valid_org(org_name: str) -> bool:
        """Check if organization name is valid."""
        org_lower = org_name.lower()
        
        # Check against noise words
        for noise in OrganizationFilter.NOISE_WORDS:
            if noise in org_lower:
                return False
        
        # Check word count (max 5 words)
        if len(org_name.split()) > 5:
            return False
        
        # Check minimum length (at least 2 words or 3+ chars)
        if len(org_name) < 3 and len(org_name.split()) < 2:
            return False
        
        return True

    @staticmethod
    def filter_organizations(text: str) -> List[str]:
        """Extract and filter organizations from text."""
        if not NLP:
            return []
        
        try:
            doc = NLP(text)
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            
            # Filter valid orgs
            filtered = [org for org in orgs if OrganizationFilter.is_valid_org(org)]
            
            # Deduplicate
            return list(set(filtered))
        except Exception as e:
            logger.debug(f"Organization filtering failed: {e}")
            return []


# ─────────────────────────────────────────────────────────────────────
# STEP 8: Clean Final Output
# ─────────────────────────────────────────────────────────────────────

class OutputCleaner:
    """Clean and structure final output."""

    @staticmethod
    def deduplicate_list(items: List[str]) -> List[str]:
        """Remove duplicates from list while preserving order."""
        seen = set()
        result = []
        for item in items:
            item_lower = item.lower()
            if item_lower not in seen:
                seen.add(item_lower)
                result.append(item)
        return result

    @staticmethod
    def clean_output(data: ResumeData) -> Dict[str, Any]:
        """Clean and structure output for JSON."""
        result = {
            "name": data.name.strip() if data.name else "",
            "email": data.email.strip() if data.email else "",
            "phone": data.phone[0] if data.phone else "",
            "skills": OutputCleaner.deduplicate_list(data.skills),
            "education": data.education,
            "experience": data.experience,
            "organizations": OutputCleaner.deduplicate_list(data.organizations),
        }
        
        # Remove empty fields
        return {k: v for k, v in result.items() if v}


# ─────────────────────────────────────────────────────────────────────
# STEP 9: Main Orchestrator
# ─────────────────────────────────────────────────────────────────────

class UniversalResumeParser:
    """Universal Resume Parser - 9-step pipeline."""

    def __init__(self):
        """Initialize parser."""
        logger.info("Initializing Universal Resume Parser")
        self.text_extractor = TextExtractor()
        self.section_detector = SectionDetector()
        self.contact_extractor = ContactExtractor()
        self.skill_extractor = SkillExtractor()
        self.education_extractor = EducationExtractor()
        self.experience_extractor = ExperienceExtractor()
        self.org_filter = OrganizationFilter()
        self.output_cleaner = OutputCleaner()

    def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse resume file through 9-step pipeline."""
        logger.info(f"Starting parsing: {file_path}")
        
        try:
            # STEP 1: Text Extraction
            logger.debug("Step 1: Text Extraction")
            raw_text = self.text_extractor.extract(file_path)
            text = self.text_extractor.clean_text(raw_text)
            logger.debug(f"Extracted {len(text)} characters")
            
            # STEP 2: Section Detection
            logger.debug("Step 2: Section Detection")
            sections = self.section_detector.detect_sections(text)
            logger.debug(f"Detected sections: {list(sections.keys())}")
            
            # STEP 3: Contact Extraction
            logger.debug("Step 3: Contact Extraction")
            contact_text = sections.get("contact", "") + " " + text[:500]
            name, email, phones = self.contact_extractor.extract_contact(contact_text)
            logger.debug(f"Contact: {name} | {email} | {phones}")
            
            # STEP 4: Skill Extraction
            logger.debug("Step 4: Skill Extraction")
            skills_section = sections.get("skills", "") or text
            skills = self.skill_extractor.extract_skills(skills_section)
            logger.debug(f"Skills found: {len(skills)}")
            
            # STEP 5: Education Extraction
            logger.debug("Step 5: Education Extraction")
            education_section = sections.get("education", "")
            education = self.education_extractor.extract_education(education_section)
            logger.debug(f"Education entries: {len(education)}")
            
            # STEP 6: Experience Extraction
            logger.debug("Step 6: Experience Extraction")
            experience_section = sections.get("experience", "")
            experience = self.experience_extractor.extract_experience(experience_section)
            logger.debug(f"Experience entries: {len(experience)}")
            
            # STEP 7: Organization Filtering
            logger.debug("Step 7: Organization Filtering")
            org_text = experience_section + " " + sections.get("projects", "")
            organizations = self.org_filter.filter_organizations(org_text)
            logger.debug(f"Organizations found: {len(organizations)}")
            
            # STEP 8: Clean Final Output
            logger.debug("Step 8: Clean Final Output")
            resume_data = ResumeData(
                name=name,
                email=email,
                phone=phones[0] if phones else "",
                skills=skills,
                education=education,
                experience=experience,
                organizations=organizations,
                summary=sections.get("summary", "")[:500]
            )
            
            output = self.output_cleaner.clean_output(resume_data)
            logger.info("Parsing completed successfully")
            
            return {
                "success": True,
                "data": output
            }
        
        except Exception as e:
            logger.error(f"Parsing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def parse_text(self, text: str) -> Dict[str, Any]:
        """Parse resume from raw text."""
        logger.info("Starting text parsing")
        
        try:
            # STEP 1: Clean text
            text = self.text_extractor.clean_text(text)
            
            # STEP 2: Section Detection
            sections = self.section_detector.detect_sections(text)
            
            # STEP 3: Contact Extraction
            contact_text = sections.get("contact", "") + " " + text[:500]
            name, email, phones = self.contact_extractor.extract_contact(contact_text)
            
            # STEP 4: Skill Extraction
            skills_section = sections.get("skills", "") or text
            skills = self.skill_extractor.extract_skills(skills_section)
            
            # STEP 5: Education Extraction
            education_section = sections.get("education", "")
            education = self.education_extractor.extract_education(education_section)
            
            # STEP 6: Experience Extraction
            experience_section = sections.get("experience", "")
            experience = self.experience_extractor.extract_experience(experience_section)
            
            # STEP 7: Organization Filtering
            org_text = experience_section + " " + sections.get("projects", "")
            organizations = self.org_filter.filter_organizations(org_text)
            
            # STEP 8: Clean Final Output
            resume_data = ResumeData(
                name=name,
                email=email,
                phone=phones[0] if phones else "",
                skills=skills,
                education=education,
                experience=experience,
                organizations=organizations
            )
            
            output = self.output_cleaner.clean_output(resume_data)
            logger.info("Text parsing completed successfully")
            
            return {
                "success": True,
                "data": output
            }
        
        except Exception as e:
            logger.error(f"Text parsing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Global parser instance (STEP 9: Performance - loaded once)
_parser_instance = None

def get_parser() -> UniversalResumeParser:
    """Get global parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = UniversalResumeParser()
        logger.info("Global parser instance created")
    return _parser_instance
