# AI Resume Parser

Production-focused full stack resume parsing and job matching system that extracts structured candidate data from PDF and DOCX files using NLP and ML, then scores and ranks resumes against job descriptions.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=000)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-3.7-09A3D5)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.3-F7931E?logo=scikitlearn&logoColor=white)

## Overview

An end-to-end AI-powered hiring support platform:

1. Upload resumes (PDF or DOCX) via UI or REST API
2. Extract and clean raw text from files
3. Detect resume sections and candidate entities using spaCy NLP
4. Parse skills, education, work experience, and contact details
5. Match resumes against job descriptions using a dual-vectorization pipeline (TF-IDF + SBERT)
6. Score, grade, and rank candidates with explainable results
7. Store match history in SQLite, view results on a live dashboard

## Workflow

![Workflow Screenshot 1](https://github.com/user-attachments/assets/35078ce8-9c8c-4435-9bc8-9273cdaa4c69)
![Workflow Screenshot 2](https://github.com/user-attachments/assets/89747018-eab5-4741-8ce0-1eab61a51114)

### Processing Pipeline

```
Resume Upload (PDF / DOCX)
        │
        ▼
File parsing & raw text extraction  ←── PyMuPDF / pdfplumber / python-docx
        │
        ▼
Text cleanup & section isolation    ←── regex + section alias mapping
        │
        ▼
NLP entity extraction               ←── spaCy en_core_web_md (NER + dep parse)
        │
        ▼
Structured field parsing            ←── skills taxonomy, phone, email, education
        │
        ▼
Job Description matching            ←── TF-IDF + SBERT dual vectorization
        │
        ▼
Match scoring & grading             ←── weighted score formula (see ML Models)
        │
        ▼
Structured JSON output + Dashboard
```

## ML Models

The project uses **three trained model artifacts** stored in `backend/models/` and one pretrained language model loaded at runtime.

### 1. TF-IDF Vectorizer (`tfidf_vectorizer.pkl`)

- **Algorithm:** `sklearn.feature_extraction.text.TfidfVectorizer`
- **Purpose:** Converts resume and job description text into sparse 5,000-feature term-frequency vectors
- **Usage:** Computes keyword-level cosine similarity between a resume and a JD
- **Weight in final score:** 5%
- **Trained on:** Domain-specific job description corpora (see `train_models.py`)

### 2. SVD Transformer (`svd_transformer.pkl`)

- **Algorithm:** `sklearn.decomposition.TruncatedSVD`
- **Purpose:** Reduces the TF-IDF sparse matrix to a dense latent semantic space (dimensionality reduction / LSA)
- **Usage:** Improves keyword matching accuracy by capturing latent topic relationships
- **Trained on:** Same corpus as TF-IDF vectorizer, applied post-vectorization

### 3. SVM Classifier (`svm_classifier.pkl`) + Scaler (`scaler.pkl`)

- **Algorithm:** `sklearn.svm.SVC` with a `StandardScaler` pre-processor
- **Purpose:** Binary classification of feature vectors as `good match (1)` or `poor match (0)`
- **Input features:** `num_skills`, `num_entities`, `num_education`, `has_email`, `has_phone`, `text_length`, `num_words`
- **Scaler:** `StandardScaler` normalizes all input features before classification
- **Trained on:** Labeled resume-JD feature pairs (`train_models.py → train_ml_classifier()`)

### 4. Sentence-BERT — `all-MiniLM-L6-v2` (runtime, pretrained)

- **Source:** `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace)
- **Purpose:** Generates dense 384-dimensional semantic embeddings for deep meaning-aware similarity
- **Usage:** Cosine similarity between resume embedding and JD embedding
- **Weight in final score:** 45%
- **Loading:** Lazy-loaded at first request; supports INT8 quantization via ONNX Runtime (`optimum`)

### Scoring Formula

```
Final Score = 45% × SBERT semantic cosine
            + 35% × Skills taxonomy keyword recall
            +  5% × TF-IDF sparse cosine
            + 15% × Structural section presence bonus
```

Grades: **A** (≥ 85), **B** (≥ 70), **C** (≥ 55), **D** (< 55)

### Retrain Models

```bash
cd backend
python train_models.py
```

## Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| Web framework | Flask 3.0, Flask-CORS, Flask-Smorest |
| NLP | spaCy 3.7 (`en_core_web_md`), phonenumbers, regex |
| ML / Similarity | scikit-learn 1.3, sentence-transformers, ONNX Runtime |
| Async tasks | Celery, Redis, Flask-SocketIO |
| Database | SQLAlchemy 2.0, Flask-Migrate, Alembic, SQLite |
| Production server | Gunicorn |

### Frontend

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript 5 |
| Build tool | Vite 6 |
| Styling | Tailwind CSS |
| State management | Zustand |
| Data fetching | TanStack Query |
| Animations | Framer Motion |

### File Parsing

| Format | Library |
|---|---|
| PDF | PyMuPDF, pdfplumber, PyPDF2 |
| DOCX | python-docx |
| Plain text | Built-in |

## Project Structure

```text
resume-parser/
├── run.py                          # Root launcher (delegates to backend/run.py)
├── requirements.txt                # Root dev/CI dependencies
├── README.md
│
├── backend/
│   ├── run.py                      # Flask app entry point
│   ├── config.py                   # Environment-based configuration
│   ├── gunicorn.conf.py            # Production WSGI config
│   ├── train_models.py             # ML model training script
│   ├── resume_parser_production.py # Core spaCy-based resume parser module
│   ├── requirements.txt            # Python dependencies
│   ├── pytest.ini                  # Test configuration
│   │
│   ├── app/
│   │   ├── __init__.py             # Flask app factory (create_app)
│   │   ├── extensions.py           # Flask extensions (db, migrate, limiter)
│   │   ├── cache.py                # LRU / Redis caching layer
│   │   ├── tasks.py                # Celery async task definitions
│   │   ├── celery_app.py           # Celery application setup
│   │   ├── socketio_ext.py         # Flask-SocketIO setup
│   │   │
│   │   ├── blueprints/
│   │   │   ├── api/                # REST API routes (v1)
│   │   │   ├── ui/                 # Server-side UI routes
│   │   │   ├── dashboard.py        # Dashboard blueprint
│   │   │   ├── match.py            # Resume-JD matching blueprint
│   │   │   └── upload.py           # File upload blueprint
│   │   │
│   │   ├── core/
│   │   │   ├── extractor.py        # Universal section/entity extractor
│   │   │   ├── section_aliases.py  # Section heading alias map
│   │   │   └── skill_dict.py       # Skills taxonomy dictionary
│   │   │
│   │   ├── models/
│   │   │   ├── resume.py           # Resume domain model
│   │   │   ├── resume_profile.py   # Structured candidate profile
│   │   │   ├── resume_model.py     # ORM-integrated resume model
│   │   │   ├── job.py              # Job description model
│   │   │   ├── matcher.py          # Matcher orchestration model
│   │   │   ├── match_result.py     # Match scoring result + grading
│   │   │   └── db_models.py        # SQLAlchemy MatchHistory table
│   │   │
│   │   ├── services/
│   │   │   ├── nlp_service.py          # spaCy NER, section parsing, entity extraction
│   │   │   ├── ml_service.py           # Dual-vector matching (TF-IDF + SBERT)
│   │   │   ├── similarity_service.py   # TF-IDF + SVD model loading and inference
│   │   │   ├── ml_inference_service.py # SVM classifier inference
│   │   │   ├── file_service.py         # PDF / DOCX text extraction
│   │   │   ├── ats_service.py          # ATS score computation
│   │   │   ├── career_analyzer.py      # Career trajectory analysis
│   │   │   ├── resume_matcher_service.py # End-to-end match orchestration
│   │   │   ├── job_scraper_service.py  # Job listing ingestion
│   │   │   └── universal_parser_service.py # Universal file parser wrapper
│   │   │
│   │   ├── use_cases/              # Application use-case handlers
│   │   ├── utils/                  # Validators, logger, config helpers, skills dict
│   │   ├── static/                 # CSS and JS assets
│   │   └── templates/              # Jinja2 HTML templates
│   │
│   ├── models/
│   │   ├── tfidf_vectorizer.pkl    # Trained TF-IDF vectorizer
│   │   ├── svd_transformer.pkl     # Trained SVD (LSA) transformer
│   │   ├── svm_classifier.pkl      # Trained SVM match classifier
│   │   ├── scaler.pkl              # Feature StandardScaler
│   │   └── resume_matcher.pkl      # Composite matcher artifact
│   │
│   ├── migrations/                 # Alembic DB migration scripts
│   │   └── 001_match_history.py
│   │
│   └── tests/
│       ├── conftest.py             # Pytest fixtures and app setup
│       ├── test_nlp_service.py     # NLP extraction tests (49 tests)
│       ├── test_ml_service.py      # ML scoring tests
│       ├── test_file_service.py    # File parsing tests
│       ├── test_api_v1.py          # Full API route tests
│       ├── test_universal_parser.py
│       ├── unit/                   # Isolated unit tests
│       ├── integration/            # Full request-cycle integration tests
│       └── fixtures/               # Test data files
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── api/                    # Axios API client wrappers
│       ├── components/             # Reusable UI components
│       ├── store/                  # Zustand state stores
│       └── types/                  # TypeScript type definitions
│
└── docs/
    ├── UNIVERSAL_PARSER.md
    ├── architecture/
    └── reports/
```

## Run Locally

### 1. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python run.py
```

Backend: http://localhost:5000
Health check: http://localhost:5000/api/dashboard/health

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Testing

```bash
# All tests
python -m pytest backend/tests/ -q

# NLP unit tests only (49 tests)
python -m pytest backend/tests/test_nlp_service.py -q

# With coverage
python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing
```

## Output Example

```json
{
  "name": "Kamalesh B",
  "email": "kamalesh@example.com",
  "phone": "+91-98765-43210",
  "skills": ["Python", "Flask", "React", "spaCy", "scikit-learn"],
  "education": [
    { "degree": "B.Tech Computer Science", "institution": "Anna University", "year_range": "2020-2024" }
  ],
  "experience": [
    { "title": "Software Engineer", "company": "Example Corp", "duration": "2 years" }
  ],
  "match_score": 87.4,
  "grade": "A",
  "matched_keywords": ["Python", "Flask", "REST API"],
  "missing_keywords": ["Kubernetes", "Terraform"]
}

## Notes

- Docker and Ruff were intentionally removed from this repository.
- This README is the single authoritative documentation file for setup and workflow.


