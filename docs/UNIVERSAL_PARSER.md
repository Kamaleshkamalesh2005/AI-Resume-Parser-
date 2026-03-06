# Universal Resume Parser - Production Architecture

## Overview

A robust, 9-step production pipeline for parsing resumes in multiple formats (PDF, DOCX) with support for different resume structures and layouts.

## Architecture: 9-Step Pipeline

### STEP 1: Text Extraction
**File**: `app/core/extractor.py:TextExtractor`

Supports:
- PDF extraction using PyMuPDF
- DOCX extraction using python-docx
- Automatic format detection
- Text cleaning:
  - Remove extra whitespace
  - Fix broken lines (PDF artifacts)
  - Normalize encoding

```python
from app.core import get_parser
parser = get_parser()
text = TextExtractor.extract("resume.pdf")
cleaned = TextExtractor.clean_text(text)
```

### STEP 2: Section Detection
**File**: `app/core/extractor.py:SectionDetector`

Uses heading aliases and fuzzy matching to detect sections:

```python
sections = {
    "contact": "...",
    "education": "...",
    "experience": "...",
    "skills": "...",
    "projects": "...",
    "certifications": "...",
    "summary": "..."
}
```

**Heading Aliases**: See `app/core/section_aliases.py`

Example:
- Education → ["education", "academic background", "academic qualification"]
- Experience → ["work experience", "professional experience", "employment history"]
- Skills → ["skills", "technical skills", "core competencies", "technologies"]

Fuzzy matching threshold: 70% similarity

### STEP 3: Contact Extraction
**File**: `app/core/extractor.py:ContactExtractor`

Extracts from first 15 lines:
- **Name**: First sequence of 2-3 capitalized words
- **Email**: RFC regex pattern
- **Phone**: International format support

```python
name, email, phones = ContactExtractor.extract_contact(text)
# Returns: ("John Doe", "john@example.com", ["123-456-7890"])
```

### STEP 4: Skill Extraction
**File**: `app/core/extractor.py:SkillExtractor`

**No NER dependency** — uses predefined skill dictionary:

- Programming: Python, Java, JavaScript, C++, C#, Ruby, Go, Rust, etc.
- Web: React, Angular, Vue, Django, Flask, Spring Boot, Node.js, etc.
- Cloud: AWS, Azure, GCP, Heroku, etc.
- DevOps: Docker, Kubernetes, Git, Jenkins, Terraform, Ansible, etc.
- ML/AI: TensorFlow, PyTorch, Scikit-learn, spaCy, HuggingFace, etc.
- Databases: SQL, MongoDB, PostgreSQL, DynamoDB, Redis, Cassandra, etc.
- Testing: Jest, Mocha, PyTest, Selenium, Cypress, etc.
- And 10+ more categories

See `app/core/skill_dict.py` for complete list.

```python
skills = SkillExtractor.extract_skills(text)
# Returns: ["Python", "React", "Docker", "AWS"]
```

### STEP 5: Education Extraction
**File**: `app/core/extractor.py:EducationExtractor`

Runs **only on EDUCATION section** (no section leakage).

Detects:
- Degree: Bachelor, Master, PhD, B.Tech, MBA, etc.
- Institution: University, College, Institute, etc.
- Year range: (19|20)\d{2}

```python
education = EducationExtractor.extract_education(education_section)
# Returns: [
#   {"degree": "Bachelor", "institution": "MIT", "year_range": "2018 - 2022"},
#   {"degree": "Master", "institution": "Stanford", "year_range": "2022 - 2024"}
# ]
```

### STEP 6: Experience Extraction
**File**: `app/core/extractor.py:ExperienceExtractor`

Runs **only on EXPERIENCE section** (no section leakage).

Detects:
- Job title: Keywords (Engineer, Developer, Analyst, Scientist, Manager, etc.)
- Company: spaCy ORG NER
- Duration: Multiple formats supported

```python
experience = ExperienceExtractor.extract_experience(experience_section)
# Returns: [
#   {"job_title": "Senior Engineer", "company": "Google", "duration": "Jan 2022 – Present"},
#   {"job_title": "Developer", "company": "Microsoft", "duration": "2020 – 2022"}
# ]
```

### STEP 7: Organization Filtering
**File**: `app/core/extractor.py:OrganizationFilter`

Filters spaCy ORG entities:
- Removes technical terms (Python, Java, Docker, etc.)
- Removes degree words (Bachelor, Master, etc.)
- Max 5 words per organization
- Deduplicates results

```python
orgs = OrganizationFilter.filter_organizations(text)
# Returns: ["Google", "Microsoft", "GitHub"]
```

### STEP 8: Clean Final Output
**File**: `app/core/extractor.py:OutputCleaner`

Produces structured JSON:

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "123-456-7890",
  "skills": ["Python", "React", "Docker", "AWS"],
  "education": [
    {
      "degree": "Bachelor",
      "institution": "MIT",
      "year_range": "2018 - 2022"
    }
  ],
  "experience": [
    {
      "job_title": "Senior Engineer",
      "company": "Google",
      "duration": "Jan 2022 – Present"
    }
  ],
  "organizations": ["Google", "Microsoft"]
}
```

Features:
- Remove duplicates
- Remove empty fields
- Correct section mapping
- Deduplication with case-insensitive matching

### STEP 9: Performance Optimization
**File**: `app/core/extractor.py:get_parser()`

- **Global singleton**: Parser loaded once at startup
- **Compiled regex**: All patterns pre-compiled
- **Single NLP pass**: spaCy model loaded once
- **Efficient matching**: Fuzzy matching with early exit
- **Debug logging**: Comprehensive logging for debugging

```python
from app.core import get_parser
parser = get_parser()  # Singleton instance
```

## Usage

### Parse Resume File

```python
from app.services.universal_parser_service import get_parser_service

service = get_parser_service()
result = service.parse_file("resume.pdf")

if result["success"]:
    data = result["data"]
    print(f"Name: {data['name']}")
    print(f"Skills: {', '.join(data['skills'])}")
else:
    print(f"Error: {result['error']}")
```

### Parse Resume Text

```python
from app.services.universal_parser_service import get_parser_service

resume_text = """
John Doe
john@example.com | 123-456-7890

PROFESSIONAL SUMMARY
...

EXPERIENCE
...

EDUCATION
...
"""

service = get_parser_service()
result = service.parse_text(resume_text)
```

### API Endpoints

#### Upload Resume
```
POST /api/upload/resume
Content-Type: multipart/form-data

file: <PDF or DOCX file>

Response:
{
  "success": true,
  "data": { ... parsed resume ... },
  "message": "Resume parsed successfully"
}
```

#### Batch Upload
```
POST /api/upload/batch
Content-Type: multipart/form-data

files: <multiple files>

Response:
{
  "success": true,
  "data": [ ... array of parsed resumes ... ],
  "failed": [ ... array of errors ... ],
  "summary": {
    "total": 10,
    "successful": 9,
    "failed": 1
  }
}
```

#### Parse Job Description
```
POST /api/upload/job-description
Content-Type: application/x-www-form-urlencoded

text: "Job description text..." OR file: <PDF/DOCX>

Response:
{
  "success": true,
  "data": {
    "text": "...",
    "skills_detected": ["Python", "React", "Docker"],
    "text_length": 1200
  }
}
```

## Project Structure

```
C:\Users\kamal\Downloads\resume parser new\
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── blueprints/          # API and UI routes
│   │   ├── models/              # Database models
│   │   ├── services/            # Business logic
│   │   ├── core/                # NEW: Universal Parser Core
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py     # 9-step pipeline
│   │   │   ├── skill_dict.py    # Predefined skills
│   │   │   └── section_aliases.py # Heading aliases
│   │   └── utils/
│   ├── migrations/
│   ├── tests/
│   ├── config.py
│   ├── run.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── docker-compose.yml
├── Dockerfile
├── UNIVERSAL_PARSER.md           # This file
├── README.md
└── .gitignore
```

## Dependencies

Core dependencies (already in requirements.txt):

- **PyMuPDF** (fitz): `pip install PyMuPDF`
- **python-docx**: `pip install python-docx`
- **spaCy**: `pip install spacy && python -m spacy download en_core_web_sm`
- **Flask**: `pip install flask`

## Testing

```bash
# Test individual components
python -c "from app.core public import get_parser; p = get_parser(); print(p.parse('resume.pdf'))"

# Run full test suite
pytest tests/ -v

# Test with sample resume
python -c "
from app.services.universal_parser_service import get_parser_service
service = get_parser_service()
result = service.parse_file('test_resume.pdf')
import json
print(json.dumps(result, indent=2))
"
```

## Troubleshooting

### "PyMuPDF not installed"
```bash
pip install PyMuPDF
```

### "python-docx not installed"
```bash
pip install python-docx
```

### "spaCy model not found"
```bash
python -m spacy download en_core_web_sm
```

### "No sections detected"
Check `app/core/section_aliases.py` for heading aliases. Add missing variations.

### "Skills not detected"
Skills must be in `app/core/skill_dict.py`. Add custom skills to `SKILLS_DICT`.

### Low accuracy on specific resume format
1. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Check section detection:
   ```python
   sections = SectionDetector.detect_sections(text)
   print(sections)
   ```

3. Verify heading aliases match your resume format
4. Add custom aliases to `SECTION_ALIASES`

## Performance Metrics

- **Text extraction**: ~100-500ms (PDF size dependent)
- **Section detection**: ~10-50ms
- **Contact extraction**: ~5-10ms
- **Skill extraction**: ~20-100ms (text length dependent)
- **Education extraction**: ~10-30ms
- **Experience extraction**: ~20-50ms
- **NER (orgs)**: ~50-200ms (depends on spaCy model)
- **Total**: ~200-1000ms per resume

**Optimization done**:
- ✅ spaCy model loaded once globally
- ✅ Compiled regex patterns
- ✅ Single NLP pass
- ✅ Efficient string matching
- ✅ Memory pooling for recurring objects

## Future Enhancements

- [ ] Custom skill dictionary per user/company
- [ ] Machine learning confidence scores
- [ ] Fine-tuned NER model for better org detection
- [ ] Multilingual support
- [ ] Resume formatting (preserve layout)
- [ ] Field conflict resolution (when section detection fails)
- [ ] Custom extraction rules per company
- [ ] Resume validation and quality scoring

# License

MIT

# Support

For issues, questions, or contributions, contact the development team.
