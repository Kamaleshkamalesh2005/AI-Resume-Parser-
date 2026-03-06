# Quick Start Guide

Resume Parser - Full Stack Application

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend)
- Virtual environment (Python)

## 🚀 Option 1: Run from Root Directory (Recommended)

The project includes a root-level `run.py` that automatically delegates to the backend.

### Backend Setup & Start

```bash
# Install Python dependencies (one-time)
python -m venv .venv
.venv\Scripts\activate           # On Windows
source .venv/bin/activate        # On Linux/Mac

pip install -r backend/requirements.txt

# Start the Flask backend server
python run.py
```

The backend will start on `http://localhost:5000`

### Frontend Setup & Start (in a new terminal)

```bash
cd frontend

# Install Node dependencies (one-time)
npm install

# Start the React development server
npm run dev
```

The frontend will start on `http://localhost:5173`

---

## 🚀 Option 2: Run from Backend Directory

If you prefer to run from within the backend folder:

### Backend Setup & Start

```bash
cd backend

# Create virtual environment (if not already done)
python -m venv .venv
.venv\Scripts\activate           # On Windows
source .venv/bin/activate        # On Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start Flask server
python run.py
```

Backend runs on: `http://localhost:5000`

### Frontend Setup & Start (in a new terminal from project root)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: `http://localhost:5173`

---

## 📊 API Documentation

Once the backend is running, visit: `http://localhost:5000/api/v1/docs`

## 🧪 Run Tests

### Backend Tests

```bash
# From within backend directory
pytest tests/ -v

# Or from root with path
python -m pytest backend/tests/ -v
```

### Frontend Tests

```bash
cd frontend
npm run test
```

## 🐳 Docker

Build and run with Docker Compose:

```bash
docker-compose up --build
```

This starts:
- Flask backend on `http://localhost:5000`
- React frontend on `http://localhost:3000`
- PostgreSQL database
- Redis cache

## 🛠️ Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///resume_matcher.db
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### Frontend Environment Variables

Create `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:5000/api
VITE_API_TIMEOUT=30000
```

## 📁 Directory Structure

```
resume-parser/
├── backend/              # Python Flask API
│   ├── app/             # Application code
│   ├── tests/           # Test suite
│   ├── requirements.txt
│   └── run.py
├── frontend/            # React TypeScript UI
│   ├── src/            # Source code
│   └── package.json
└── run.py              # Root-level entry point
```

## 🔧 Troubleshooting

### Template Not Found Error

If you see `jinja2.exceptions.TemplateNotFound: index.html`, ensure:

1. You're running from the correct directory
2. Flask templates are at: `backend/app/templates/`
3. Use the provided `run.py` scripts to start the app

**Solution**: Use the root-level `python run.py` or `cd backend && python run.py`

### Port Already in Use

If port 5000 or 5173 is already in use:

```bash
# Backend: Use different port
cd backend
python run.py --port 5001

# Frontend: Use different port  
cd frontend
npm run dev -- --port 3000
```

### Module Import Errors

```bash
# Ensure virtual environment is activated
.venv\Scripts\activate              # Windows
source .venv/bin/activate           # Linux/Mac

# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall
```

### Database Issues

```bash
# Reset SQLite database
rm backend/resume_matcher.db

# Reinitialize
cd backend
flask db upgrade
```

## 📚 Documentation

- **[backend/README.md](backend/README.md)** - Backend API documentation and setup
- **[frontend/README.md](frontend/README.md)** - Frontend development guide
- **[docs/UNIVERSAL_PARSER.md](docs/UNIVERSAL_PARSER.md)** - Parser architecture (9-step pipeline)
- **[RESTRUCTURING_SUMMARY.md](RESTRUCTURING_SUMMARY.md)** - Project organization overview
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide

## 🎯 Next Steps

1. ✅ Run backend: `python run.py`
2. ✅ Run frontend: `cd frontend && npm run dev`
3. ✅ Open browser: `http://localhost:5173`
4. ✅ Upload a resume to test parsing
5. ✅ View API docs: `http://localhost:5000/api/v1/docs`

---

**Status**: ✅ Production Ready | **Environment**: March 2026
