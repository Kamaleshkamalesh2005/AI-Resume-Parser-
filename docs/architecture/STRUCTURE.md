# Resume Matcher - Folder Structure Overview

```
resume-matcher/
│
├── 📁 app/                          # Main application package
│   ├── __init__.py                  # Flask app factory (create_app)
│   │
│   ├── 📁 blueprints/               # Modular routes/controllers (MVC - View layer)
│   │   ├── __init__.py
│   │   ├── upload.py                # Resume upload endpoints
│   │   │   ├── POST /api/upload/resume       - Single file upload
│   │   │   ├── POST /api/upload/batch        - Multiple files upload
│   │   │   └── POST /api/upload/validate     - File validation
│   │   │
│   │   ├── match.py                 # Matching endpoints
│   │   │   ├── POST /api/match/similarity    - Cosine similarity
│   │   │   ├── POST /api/match/batch        - Batch matching
│   │   │   ├── POST /api/match/predict      - ML prediction
│   │   │   └── GET /api/match/model-info    - Model information
│   │   │
│   │   └── dashboard.py             # Statistics endpoints
│   │       ├── GET /api/dashboard/stats     - System statistics
│   │       ├── GET /api/dashboard/health    - Health check
│   │       └── GET /api/dashboard/info      - App information
│   │
│   ├── 📁 models/                   # Data models (MVC - Model layer)
│   │   ├── __init__.py
│   │   ├── resume_model.py          # Resume data model
│   │   │   ├── Class: ResumeModel
│   │   │   ├── load_from_file()     - Load resume from disk
│   │   │   ├── parse()              - Extract information
│   │   │   └── extract_features()   - Get feature vectors
│   │   │
│   │   └── matcher.py               # ML classifier model
│   │       ├── Class: MatcherModel
│   │       ├── train()              - Train SVM
│   │       ├── predict()            - Make predictions
│   │       └── batch_predict()      - Batch predictions
│   │
│   ├── 📁 services/                 # Business logic layer
│   │   ├── __init__.py
│   │   │
│   │   ├── nlp_service.py           # NLP operations
│   │   │   ├── Class: NLPService
│   │   │   ├── extract_entities()   - Named Entity Recognition (spaCy)
│   │   │   ├── extract_skills()     - Technical skill extraction
│   │   │   ├── extract_contact_info() - Email/phone extraction
│   │   │   ├── extract_education()  - Education info
│   │   │   └── clean_text()         - Text normalization
│   │   │
│   │   ├── file_service.py          # File operations
│   │   │   ├── Class: FileService
│   │   │   ├── save_upload()        - Save uploaded file
│   │   │   ├── extract_text_from_pdf()    - PDF parsing (PyPDF2)
│   │   │   ├── extract_text_from_docx()   - DOCX parsing (python-docx)
│   │   │   ├── delete_file()        - File deletion
│   │   │   └── get_file_info()      - File metadata
│   │   │
│   │   └── similarity_service.py    # Similarity computation
│   │       ├── Class: SimilarityService
│   │       ├── train_models()       - Train TF-IDF & SVD
│   │       ├── vectorize_text()     - Convert text to vector
│   │       ├── compute_similarity() - Cosine similarity
│   │       └── batch_compute_similarity() - Batch computation
│   │
│   ├── 📁 utils/                    # Utilities
│   │   ├── __init__.py
│   │   │
│   │   ├── config.py                # Configuration management
│   │   │   ├── Class: Config        - Base configuration
│   │   │   ├── Class: DevelopmentConfig
│   │   │   ├── Class: ProductionConfig
│   │   │   └── Class: TestingConfig
│   │   │
│   │   ├── logger.py                # Logging setup
│   │   │   ├── setup_logger()       - Initialize logging
│   │   │   ├── File + Console handlers
│   │   │   ├── Rotating file handler (10MB max)
│   │   │   └── Third-party lib suppression
│   │   │
│   │   └── validators.py            # Input validation
│   │       ├── is_allowed_file()    - Extension check
│   │       ├── validate_file_upload() - Comprehensive validation
│   │       ├── extract_email()      - Regex email extraction
│   │       ├── extract_phone()      - Regex phone extraction
│   │       └── validate_text_length() - Length constraints
│   │
│   ├── 📁 templates/                # HTML templates (Jinja2)
│   │   ├── base.html                # Base layout with navbar/footer
│   │   │   ├── Navigation bar with glassmorphism
│   │   │   ├── CSS custom variables
│   │   │   ├── Neon glow effects
│   │   │   ├── Animations (fadeIn, slideIn)
│   │   │   └── Flash message display
│   │   │
│   │   ├── index.html               # Home page
│   │   │   ├── Single resume upload section
│   │   │   ├── Batch upload section
│   │   │   ├── Drag-drop zones
│   │   │   └── Results display
│   │   │
│   │   └── dashboard.html           # Statistics dashboard
│   │       ├── Health status widgets
│   │       ├── System statistics
│   │       ├── Configuration display
│   │       ├── Model information
│   │       └── Auto-refresh (30s)
│   │
│   └── 📁 static/                   # Static files
│       ├── 📁 css/
│       │   └── style.css            # Tailwind + Custom styles
│       │       ├── Glassmorphism classes
│       │       ├── Neon effects (CSS glow)
│       │       ├── Animations (spin, pulse)
│       │       ├── Responsive grid system
│       │       ├── Form styling
│       │       ├── Alerts & Badges
│       │       └── Scrollbar customization
│       │
│       └── 📁 js/
│           ├── app.js               # Global utilities
│           │   ├── apiCall()        - API request handler
│           │   ├── showNotification() - Toast notifications
│           │   ├── formatBytes()    - File size formatting
│           │   ├── formatDate()     - Date formatting
│           │   ├── debounce()       - Event optimization
│           │   └── throttle()       - Rate limiting
│           │
│           └── upload.js            # Upload functionality
│               ├── initializeUploadHandlers() - Single upload
│               ├── handleFileSelect() - File selection
│               ├── processUpload()   - Upload processing
│               ├── displayResumeResults() - Results rendering
│               ├── initializeBatchUploadHandlers() - Batch handler
│               ├── displayBatchFiles() - File list display
│               ├── processBatchUpload() - Batch processing
│               └── displayBatchResults() - Batch results
│
├── 📁 models/                       # Trained ML models (serialized)
│   ├── tfidf_vectorizer.pkl         # TF-IDF model (scikit-learn)
│   ├── svd_transformer.pkl          # SVD transformer (dimensionality reduction)
│   ├── svm_model.pkl                # SVM classifier
│   └── scaler.pkl                   # Feature scaler (StandardScaler)
│
├── 📁 logs/                         # Application logs
│   └── app.log                      # Main application log (rotating, 10MB max)
│
├── 📁 uploads/                      # Temporary uploaded files
│   ├── uuid_resume.pdf
│   ├── uuid_cover.docx
│   └── ...
│
├── 📄 requirements.txt              # Python dependencies
│   ├── Flask==3.0.0
│   ├── spacy==3.7.2 (NLP)
│   ├── PyPDF2==3.0.1 (PDF parsing)
│   ├── python-docx==0.8.11 (DOCX parsing)
│   ├── scikit-learn==1.3.2 (ML)
│   ├── numpy, pandas (Utilities)
│   ├── python-dotenv (Env config)
│   └── gunicorn==21.2.0 (Production server)
│
├── 📄 run.py                        # Application entry point
│   ├── App factory instantiation
│   ├── Startup logging
│   ├── Development server runner
│   └── Flask shell context
│
├── 📄 train_models.py               # Model training script
│   ├── train_similarity_models()
│   ├── train_ml_classifier()
│   ├── verify_nlp_model()
│   └── Summary reporting
│
├── 📄 quickstart.py                 # Quick start setup helper
│   ├── Python version check
│   ├── Dependency installation
│   ├── spaCy model download
│   ├── Environment setup
│   ├── Directory creation
│   └── Model training
│
├── 📄 .env.example                  # Environment variables template
│   ├── Flask settings
│   ├── ML configuration
│   ├── File upload limits
│   ├── Security settings
│   └── Production flags
│
├── 📄 .gitignore                    # Git ignore rules
│   ├── .env (never commit secrets)
│   ├── uploads/ (temporary files)
│   ├── logs/ (application logs)
│   ├── __pycache__/
│   │ venv/ (virtual environment)
│   └── *.pyc
│
├── 📄 README.md                     # Comprehensive documentation
│   ├── Features overview
│   ├── Architecture explanation
│   ├── Installation guide
│   ├── API documentation
│   ├── Configuration reference
│   ├── Security features
│   ├── Usage examples
│   ├── Troubleshooting
│   └── Future enhancements
│
└── 📄 DEPLOYMENT.md                 # Production deployment guide
    ├── Linux systemd setup
    ├── Nginx reverse proxy
    ├── Docker deployment
    ├── Cloud platform guides (AWS, Heroku, DigitalOcean)
    ├── Monitoring & logging
    ├── Performance optimization
    ├── Security hardening
    ├── Database integration
    └── Troubleshooting
```

## Architecture Layers

### 1. **View Layer (Blueprints)**
   - Handles HTTP requests/responses
   - Input validation
   - Response formatting
   - Error handling

### 2. **Controller Layer (Blueprints)**
   - Orchestr routes
   - Data flow management
   - Service coordination

### 3. **Model Layer**
   - Resume data structure
   - ML classifier model
   - Data persistence

### 4. **Service Layer (Business Logic)**
   - NLP operations
   - File processing
   - Similarity computation
   - No HTTP knowledge

### 5. **Utility Layer**
   - Configuration management
   - Logging setup
   - Input validation
   - Helper functions

## Technology Stack Mapping

```
HTML5 + Vanilla JS + Tailwind CSS + Custom Effects
           ↓
    REST API Endpoints
           ↓
    Flask Blueprints (MVC)
           ↓
    Services (Business Logic)
           ↓
    ML/NLP Models
           ↓
    Data Files (.pkl, logs, uploads)
```

## Data Flow

```
User Upload
    ↓
[upload.py] - Validation
    ↓
[file_service.py] - Extract text
    ↓
[resume_model.py] - Parse & process
    ↓
[nlp_service.py] - Extract entities/skills
    ↓
[similarity_service.py] - Vectorize
    ↓
[matcher.py] - Predict match
    ↓
API Response (JSON)
    ↓
Frontend (Vanilla JS) - Display results
```

## Configuration Hierarchy

```
Environment Variables (.env)
    ↓
Config Classes (config.py)
    ├── DevelopmentConfig
    ├── ProductionConfig
    └── TestingConfig
    ↓
Flask App Configuration (run.py)
    ↓
Module-level usage
```

---

This structure ensures:
- ✅ **Scalability**: Easy to add new features/modules
- ✅ **Maintainability**: Clear separation of concerns
- ✅ **Testability**: Isolated components
- ✅ **Production-ready**: Logging, error handling, configuration
- ✅ **Security**: Input validation, secure file handling
