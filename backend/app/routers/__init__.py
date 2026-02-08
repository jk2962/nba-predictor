"""NBA Player Performance Prediction - Routers Package"""
from app.routers.players import router as players_router, metrics_router
from app.routers.compare import router as compare_router

__all__ = ["players_router", "metrics_router", "compare_router"]
