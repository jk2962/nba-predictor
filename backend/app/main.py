"""
NBA Player Performance Prediction - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import get_settings
from app.database import init_db
from app.routers import players_router, metrics_router, compare_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="NBA Player Performance Prediction API",
    description="""
    API for predicting NBA player performance using machine learning.
    
    ## Features
    - Player search and filtering
    - Season statistics and recent game logs
    - Next game performance predictions with confidence intervals
    - Top performer rankings
    - Batch predictions for draft/comparison tools
    - **Player comparison tool** - Compare 2-3 players side-by-side
    
    ## Models
    Uses XGBoost regression models trained on historical player data.
    Predictions include points, rebounds, and assists with 95% confidence intervals.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(players_router)
app.include_router(metrics_router)
app.include_router(compare_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and load models on startup."""
    logger.info("Starting NBA Player Performance Prediction API...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Try to load ML models
    from app.ml import predictor
    if predictor.load_models():
        logger.info("ML models loaded successfully")
    else:
        logger.warning("ML models not found. Run seed_data.py to train models.")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "NBA Player Performance Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "ok"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
