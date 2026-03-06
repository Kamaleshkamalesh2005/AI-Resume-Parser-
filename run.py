#!/usr/bin/env python
"""
Root-level entry point that runs the backend Flask application.
This allows running the app from the project root by delegating to backend/run.py
"""

import os
import sys
import subprocess

# Run the backend Flask app from the backend directory
if __name__ == '__main__':
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    result = subprocess.run(
        [sys.executable, os.path.join(backend_dir, 'run.py')],
        cwd=backend_dir
    )
    sys.exit(result.returncode)
