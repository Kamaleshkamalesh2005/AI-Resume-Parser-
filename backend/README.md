# Backend - Resume Parser API

Flask REST API for parsing resumes and matching them with job descriptions.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (venv)

### Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Development mode
python run.py

# Production mode with Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

The API will be available at `http://localhost:5000`

## 📁 Project Structure

```
backend/
├── app/                           # Main Flask application
│   ├── blueprints/               # Route handlers
│   │   ├── api/                 # REST API endpoints
│   │   │   ├── routes.py        # Endpoint definitions
│   │   │   └── schemas.py       # Request/response schemas
│   │   └── ui/                  # UI routes (if any)
│   │
│   ├── core/                     # Core parsing logic (9-step pipeline)
│   │   ├── extractor.py         # Universal Resume Parser
│   │   ├── skill_dict.py        # Predefined skills (500+)
│   │   └── section_aliases.py   # Section heading variations
│   │
│   ├── models/                   # Database models
│   │   ├── db_models.py         # SQLAlchemy models
│   │   ├── resume_model.py      # Resume data model
│   │   └── ...
│   │
│   ├── services/                 # Business logic
│   │   ├── resume_matcher.py    # Matching logic
│   │   ├── nlp_service.py       # NLP operations
│   │   ├── file_service.py      # File operations
│   │   ├── ml_inference.py      # ML inference
│   │   └── ...
│   │
│   ├── utils/                    # Utility functions
│   │   ├── config.py            # Configuration
│   │   ├── logger.py            # Logging setup
│   │   └── validators.py        # Input validation
│   │
│   ├── static/                   # Static files (CSS, JS)
│   ├── templates/                # Jinja2 templates
│   ├── __init__.py              # Flask app factory
│   └── ...
│
├── tests/                        # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data
│
├── migrations/                   # Database migrations (Alembic)
├── uploads/                      # User uploaded files
├── logs/                         # Application logs
│
├── config.py                     # Configuration management
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── gunicorn.conf.py             # Gunicorn configuration
└── Makefile                      # Development commands
```

## 🔧 Configuration

Create a `.env` file in the backend directory:

```env
# Flask
FLASK_ENV=development
FLASK_APP=app
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///resume_matcher.db
# Or for production:
# DATABASE_URL=postgresql://user:password@localhost/resume_db

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# File uploads
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800  # 50MB

# API
API_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5000"]

# Logging
LOG_LEVEL=INFO
```

## 📚 API Endpoints

### Resume Management

#### Upload Resume
```
POST /api/upload/resume
Content-Type: multipart/form-data

Body:
- file: <PDF or DOCX file>

Response:
{
  "success": true,
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "123-456-7890",
    "skills": ["Python", "Flask", "JavaScript"],
    "education": [
      {
        "degree": "Bachelor",
        "institution": "MIT",
        "year_range": "2018 - 2022"
      }
    ],
    "experience": [
      {
        "job_title": "Software Engineer",
        "company": "Tech Corp",
        "duration": "2022 - 2024"
      }
    ],
    "organizations": ["Tech Corp", "MIT"]
  }
}
```

#### Batch Upload
```
POST /api/upload/batch
Content-Type: multipart/form-data

Body:
- files: <Multiple PDF/DOCX files>

Response:
{
  "success": true,
  "data": [
    { ... },  # Resume 1
    { ... }   # Resume 2
  ]
}
```

#### Upload Job Description
```
POST /api/upload/job-description
Content-Type: application/json

Body:
{
  "title": "Senior Python Developer",
  "description": "Looking for a Python expert with 5+ years of experience...",
  "required_skills": ["Python", "Flask", "PostgreSQL"]
}

Response:
{
  "success": true,
  "data": {
    "skills_detected": ["Python", "Flask", "PostgreSQL"],
    "job_title": "Senior Python Developer"
  }
}
```

### Resume Matching

#### Get Matches
```
POST /api/match
Content-Type: application/json

Body:
{
  "resume_id": "uuid",
  "job_description": "..."
}

Response:
{
  "success": true,
  "data": {
    "match_score": 0.85,
    "skill_matches": 12,
    "skill_gaps": 2,
    "recommendations": [...]
  }
}
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_file_service.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Integration Tests Only
```bash
pytest tests/integration/ -v
```

## 🔄 Database Migrations

### Create New Migration
```bash
flask db migrate -m "Description of changes"
```

### Apply Migrations
```bash
flask db upgrade
```

### Rollback Migration
```bash
flask db downgrade
```

## 📦 Dependencies

Key Python packages:

- **Flask** (3.0.0) - Web framework
- **Flask-SQLAlchemy** (3.1.0) - ORM
- **spaCy** (3.7.2) - NLP library
- **PyMuPDF** (1.23.2) - PDF parsing
- **python-docx** (0.8.11) - DOCX parsing
- **scikit-learn** (1.3.2) - Machine learning
- **Celery** (5.3.0) - Task queue
- **Redis** (5.0.0) - Caching

See `requirements.txt` for complete list.

## 🎯 Universal Resume Parser (9-Step Pipeline)

The heart of the backend is the Universal Resume Parser in `/app/core/extractor.py`:

### Steps
1. **Text Extraction** - Extract text from PDF/DOCX files
2. **Section Detection** - Detect sections (education, experience, skills) with fuzzy matching
3. **Contact Extraction** - Extract name, email, phone
4. **Skill Extraction** - Match against 500+ predefined skills
5. **Education Extraction** - Extract degrees, institutions, dates
6. **Experience Extraction** - Extract job titles, companies, durations
7. **Organization Filtering** - Filter noise and invalid organizations
8. **Output Cleaning** - Deduplicate and clean final output
9. **Performance Optimization** - Global singleton parser instance

### Features
- Handles multiple resume formats (PDF, DOCX)
- Robust section isolation (prevents data leakage)
- 50+ section heading aliases (handles format variations)
- 500+ predefined technical skills
- No NER dependency (faster, more predictable)
- Compiled regex patterns for performance

## 🚁 Deployment

### Local Production
```bash
gunicorn -c gunicorn.conf.py app:app
```

### Docker
```bash
docker build -t resume-parser-backend .
docker run -p 5000:5000 resume-parser-backend
```

### Docker Compose
```bash
docker-compose up --build
```

See [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed deployment guide.

## 📊 Logging

Logs are written to `/logs` directory with rotation:
- `app.log` - General application logs
- `error.log` - Error logs
- `request.log` - HTTP request logs

View logs:
```bash
tail -f logs/app.log
```

## 🐛 Troubleshooting

### Import Errors
```bash
# Ensure virtual environment is activated
.venv\Scripts\activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Database Issues
```bash
# Reset database
rm backend/resume_matcher.db
flask db upgrade
```

### Port Already in Use
```bash
# Use different port
python run.py --port 5001
```

## 📝 Notes

- The parser is production-ready and handles 200-1000ms per resume
- Section detection uses 70% fuzzy match threshold for reliability
- All paths are relative to `backend/` directory
- Database is SQLite by default (change in config.py for production)

## 🤝 Contributing

Before pushing changes:

```bash
# Run tests
pytest tests/ -v

# Check code style
pylint app/

# Format code
black app/
```

---

**Status**: ✅ Production Ready | **Parser Version**: 9-step Universal | **Last Updated**: March 2026
