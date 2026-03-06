# ───────────────────────────────────────────────────────────
#  Stage 1 – builder
# ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    PYTHONPATH=/install/lib/python3.12/site-packages \
    python -m spacy download en_core_web_sm --pip-args="--prefix=/install" && \
    PYTHONPATH=/install/lib/python3.12/site-packages \
    python -m spacy download en_core_web_md --pip-args="--prefix=/install" || true

# ───────────────────────────────────────────────────────────
#  Stage 2 – runner
# ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

LABEL org.opencontainers.image.source="https://github.com/OWNER/resume-matcher" \
      org.opencontainers.image.description="AI Resume Matcher – Flask API" \
      org.opencontainers.image.licenses="MIT"

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user (uid 1000)
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser . .

# Create writable directories
RUN mkdir -p logs models uploads feedback && \
    chown -R appuser:appuser logs models uploads feedback

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    GUNICORN_BIND=0.0.0.0:5000 \
    GUNICORN_WORKERS=4 \
    GUNICORN_TIMEOUT=120

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
