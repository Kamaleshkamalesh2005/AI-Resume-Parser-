# Resume Parser - Full Stack Application

A comprehensive resume parsing and job matching system built with Flask (backend) and React (frontend).

## 🎯 Features

- **📄 Resume Upload**: Support for PDF and DOCX formats with validation
- **📤 Batch Processing**: Upload and process multiple resumes simultaneously
- **🧠 NLP Processing**: Named Entity Recognition (NER) using spaCy
- **🔍 Skill Extraction**: Automatic identification of technical skills
- **📊 Contact Extraction**: Extract email and phone numbers using regex
- **🤖 ML Matching**: SVM classifier for resume-job matching
- **📈 Similarity Scoring**: TF-IDF + Cosine Similarity computation
- **✨ Modern UI**: Glassmorphism design with neon effects and smooth animations
- **🏥 Health Monitoring**: Application health checks and statistics dashboard
- **📝 Comprehensive Logging**: Production-level error handling and logging
- **🔐 Security**: CORS enabled, input validation, secure file handling
- **⚡ Scalable Architecture**: Modular blueprint structure for easy expansion

## 🏗️ Architecture

```
resume-matcher/
├── app/                             # Main application package
│   ├── __init__.py                  # Flask app factory
│   ├── blueprints/                  # Routes/Controllers (MVC)
│   │   ├── upload.py                # File upload endpoints
│   │   ├── match.py                 # Matching endpoints
│   │   └── dashboard.py             # Statistics endpoints
│   ├── models/                      # Data models
│   │   ├── resume_model.py          # Resume processing model
│   │   └── matcher.py               # ML matching model
│   ├── services/                    # Business logic
│   │   ├── nlp_service.py           # NLP operations
│   │   ├── file_service.py          # File operations
│   │   ├── similarity_service.py    # Similarity computation
│   │   ├── ml_inference_service.py  # ML inference
│   │   └── resume_matcher_service.py# Resume-job matching
│   ├── use_cases/                   # Application use cases
│   │   ├── upload_use_case.py       # Upload workflow
│   │   ├── matching_use_case.py     # Matching workflow
│   │   └── dashboard_use_case.py    # Dashboard workflow
│   ├── utils/                       # Utilities
│   │   ├── config.py                # Configuration management
│   │   ├── logger.py                # Logging setup
│   │   ├── validators.py            # Input validation
│   │   └── skills_dict.py           # Skills dictionary
│   ├── templates/                   # HTML templates (Jinja2)
│   │   ├── base.html                # Base layout
│   │   ├── index.html               # Home page
│   │   └── dashboard.html           # Statistics dashboard
│   └── static/                      # Static assets
│       ├── css/style.css            # Tailwind + custom styles
│       └── js/
│           ├── app.js               # Global utilities
│           └── upload.js            # Upload handlers
├── resume_parser_production.py      # Production resume parser (NLP)
├── train_models.py                  # ML model training script
├── quickstart.py                    # Automated setup helper
├── docs/                            # Documentation
│   ├── architecture/                # Architecture docs
│   └── reports/                     # Summary reports
├── models/                          # Trained ML models (.pkl)
├── logs/                            # Application logs
├── uploads/                         # Temporary file storage
├── requirements.txt                 # Python dependencies
├── run.py                           # Application entry point
├── Dockerfile                       # Docker containerization
├── docker-compose.yml               # Docker Compose config
├── gunicorn.conf.py                 # Gunicorn settings
├── .env.example                     # Environment template
└── README.md                        # This file
```

## 🔧 Tech Stack

### Backend
- **Framework**: Flask 3.0.0
- **NLP**: spaCy 3.7.2 (Named Entity Recognition)
- **ML**: scikit-learn 1.3.2 (SVM, TF-IDF, SVD)
- **Document Parsing**: PyPDF2 3.0.1, python-docx 0.8.11
- **Pattern Matching**: regex 2023.10.3 (Email/Phone extraction)
- **Server**: Gunicorn 21.2.0 (Production)

### Frontend
- **HTML5**: Semantic markup
- **CSS**: Tailwind CSS 2.2.19 + Custom Glassmorphism effects
- **JavaScript**: Vanilla JS (no dependencies)
- **Effects**: Neon lighting, smooth animations, gradient backgrounds

### Database
- **File Storage**: Local filesystem (pkl format for models)
- **Logging**: Rotating file handler

## 📋 Installation & Setup

### Prerequisites
- Python 3.8+
- pip or conda
- 2GB+ disk space for spaCy models

### Step 1: Clone Repository
```bash
cd resume parser new
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Download spaCy Model
```bash
python -m spacy download en_core_web_sm
```

### Step 5: Create Environment File
```bash
# Create .env file in root directory
echo FLASK_ENV=development > .env
echo SECRET_KEY=your-secret-key >> .env
```

### Step 6: Run Application
```bash
python run.py
```

Visit: `http://localhost:5000`

## 🚀 Production Deployment

### Using Gunicorn
```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 run:app
```

### Using Docker (Optional)
```bash
# Build image
docker build -t resume-matcher .

# Run container
docker run -p 5000:5000 resume-matcher
```

### Environment Variables
Set in production:
```bash
FLASK_ENV=production
SECRET_KEY=<random-secure-key>
```

## 📡 API Documentation

### Upload Endpoints

#### Single Resume Upload
```
POST /api/upload/resume
Content-Type: multipart/form-data

Body: file (PDF or DOCX)

Response:
{
    "success": true,
    "data": {
        "skills": ["Python", "Flask", ...],
        "contact_info": {"emails": [...], "phones": [...]},
        "education": ["Bachelor of Science"],
        "features": {...},
        ...
    }
}
```

#### Batch Upload
```
POST /api/upload/batch
Content-Type: multipart/form-data

Body: files[] (multiple files)

Response:
{
    "success": true,
    "data": [{...}, {...}],
    "failed": [{filename, error}],
    "summary": {total, successful, failed}
}
```

### Matching Endpoints

#### Similarity Computation
```
POST /api/match/similarity
Content-Type: application/json

{
    "resume_text": "...",
    "job_description": "..."
}

Response:
{
    "success": true,
    "similarity_score": 0.75,
    "is_match": true,
    "threshold": 0.3
}
```

#### Batch Matching
```
POST /api/match/batch
Content-Type: application/json

{
    "resume_text": "...",
    "job_descriptions": ["...", "...", ...]
}

Response:
{
    "success": true,
    "matches": [
        {
            "job_description": "...",
            "similarity_score": 0.75,
            "is_match": true
        }
    ],
    "matched_count": 1,
    "total_jobs": 3
}
```

#### ML Prediction
```
POST /api/match/predict
Content-Type: application/json

{
    "features": {
        "num_skills": 15,
        "num_education": 2,
        ...
    }
}

Response:
{
    "success": true,
    "prediction": {
        "match": true,
        "probability": 0.87,
        "confidence": 0.92
    }
}
```

### Dashboard Endpoints

#### Statistics
```
GET /api/dashboard/stats

Response:
{
    "success": true,
    "models": {...},
    "uploads": {...},
    "system": {...},
    "config": {...}
}
```

#### Health Check
```
GET /api/dashboard/health

Response:
{
    "success": true,
    "status": "healthy",
    "components": {...}
}
```

#### Application Info
```
GET /api/dashboard/info

Response:
{
    "success": true,
    "app": {...},
    "features": [...],
    "endpoints": {...}
}
```

## 🔐 Security Features

- **CORS Protection**: Configured cross-origin policies
- **File Validation**: Extension and name validation
- **Input Sanitization**: Secure filename handling
- **Error Handling**: Comprehensive exception handling
- **Logging**: All operations logged for audit trail
- **Session Security**: Secure cookie settings
- **Rate Limiting**: Ready for add-on middleware

## 📊 Configuration

Edit `app/utils/config.py`:

```python
# NLP Settings
SPACY_MODEL = 'en_core_web_sm'

# ML Settings
TF_IDF_MAX_FEATURES = 5000
SVD_N_COMPONENTS = 100
COSINE_SIMILARITY_THRESHOLD = 0.3

# File Upload
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}
```

## 📝 Logging

Logs are stored in `logs/app.log` with rotation:
- Max file size: 10 MB
- Backup count: 10 files
- Log level: Configurable (DEBUG, INFO, WARNING, ERROR)

View logs:
```bash
tail -f logs/app.log
```

## 🧪 Testing

### Manual API Testing with curl
```bash
# Single upload
curl -X POST -F "file=@resume.pdf" http://localhost:5000/api/upload/resume

# Similarity check
curl -X POST -H "Content-Type: application/json" \
  -d '{"resume_text":"Python Flask", "job_description":"Python developer"}' \
  http://localhost:5000/api/match/similarity

# Health check
curl http://localhost:5000/api/dashboard/health
```

### Python Testing
```python
import requests

response = requests.post(
    'http://localhost:5000/api/upload/resume',
    files={'file': open('resume.pdf', 'rb')}
)
print(response.json())
```

## 📚 Usage Examples

### Using the Web Interface
1. Open `http://localhost:5000` in browser
2. Drag & drop resume or click to browse
3. View extracted skills, education, contact info
4. Use batch upload for multiple resumes
5. Check dashboard for system statistics

### Using Python SDK (Create `client.py`)
```python
import requests

class ResumeMatcherClient:
    def __init__(self, base_url='http://localhost:5000/api'):
        self.base_url = base_url
    
    def upload_resume(self, filepath):
        with open(filepath, 'rb') as f:
            response = requests.post(
                f'{self.base_url}/upload/resume',
                files={'file': f}
            )
        return response.json()
    
    def match_resume(self, resume_text, job_description):
        response = requests.post(
            f'{self.base_url}/match/similarity',
            json={
                'resume_text': resume_text,
                'job_description': job_description
            }
        )
        return response.json()

# Usage
client = ResumeMatcherClient()
result = client.upload_resume('resume.pdf')
print(result)
```

## 🐛 Troubleshooting

### spaCy Model Not Found
```bash
python -m spacy download en_core_web_sm
```

### Port 5000 Already in Use
```bash
# Use different port
python run.py --port 8000
```

### CORS Errors
All CORS is enabled in `app/__init__.py`. Update if needed:
```python
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000"]}})
```

### Large Files Upload Issue
Increase `MAX_CONTENT_LENGTH` in `config.py` or nginx config

## 📈 Performance Optimization

- TF-IDF dimensionality reduction with SVD (100 components)
- Vectorization caching for repeated comparisons
- Async file processing ready
- Batch operations supported
- Model serialization with pickle

## 🔄 Future Enhancements

- [ ] Database integration (PostgreSQL)
- [ ] User authentication & authorization
- [ ] Resume templates & formatting
- [ ] Video interview parsing
- [ ] Advanced NLP with transformers (BERT)
- [ ] Real-time job scraping
- [ ] Automated job matching scheduler
- [ ] Analytics dashboard with charts
- [ ] Export results to PDF/CSV
- [ ] Mobile app (React Native)

## 📄 License

MIT License - Feel free to use and modify

## 👨‍💻 Author

Your Name
- Portfolio: [Your Portfolio]
- Email: [Your Email]
- GitHub: [Your GitHub]

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

For issues, questions, or suggestions:
- Open GitHub Issue
- Email: support@example.com
- Documentation: Check `/api/dashboard/info`

## ✨ Acknowledgments

- Flask for the web framework
- spaCy for NLP capabilities
- scikit-learn for ML algorithms
- Tailwind CSS for styling
- PyPDF2 & python-docx for document parsing

---

**Built with ❤️ for production-grade AI applications**

Last Updated: 2024
Version: 1.0.0
#   A I - R e s u m e - P a r s e r 
 
 
