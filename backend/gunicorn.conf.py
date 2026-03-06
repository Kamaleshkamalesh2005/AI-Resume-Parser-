"""
Gunicorn production configuration.
Loaded via: gunicorn -c gunicorn.conf.py run:app
"""

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.getenv("GUNICORN_WORKERS", max(2, multiprocessing.cpu_count() // 2)))
threads = int(os.getenv("GUNICORN_THREADS", 2))
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 5))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
capture_output = True
