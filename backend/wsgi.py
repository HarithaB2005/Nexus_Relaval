"""
Production WSGI entry point for gunicorn
Ensures proper initialization for production deployment
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Set environment for production
os.environ.setdefault("ENV", "production")

from main import app

if __name__ == "__main__":
    # This is called by gunicorn
    # gunicorn backend.wsgi:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    pass
