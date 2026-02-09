"""
Vercel Serverless Function Entry Point for FastAPI Backend
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app
from mangum import Mangum

# Wrap FastAPI app with Mangum for serverless compatibility
handler = Mangum(app, lifespan="off")
