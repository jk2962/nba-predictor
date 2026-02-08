"""
NBA Player Performance Prediction - Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ============== Player Schemas ==============

class PlayerBase(BaseModel):
    """Base player schema."""
    name: str
    team: Optional[str] = None
    team_abbreviation: Optional[str] = None
    position: Optional[str] = None


class PlayerCreate(PlayerBase):
    """Schema for creating a player."""
    nba_id: int
    height: Optional[str] = None
    weight: Optional[str] = None
    headshot_url: Optional[str] = None


class PlayerListItem(PlayerBase):
    """Schema for player list items."""
    id: int
    nba_id: int
    headshot_url: Optional[str] = None
    is_active: bool
    
    # Aggregated stats
    season_ppg: Optional[float] = Field(None, description="Points per game this season")
    season_rpg: Optional[float] = Field(None, description="Rebounds per game this season")
    season_apg: Optional[float] = Field(None, description="Assists per game this season")
    
    class Config:
        from_attributes = True


class PlayerDetail(PlayerListItem):
    """Detailed player schema with full stats."""
    height: Optional[str] = None
    weight: Optional[str] = None
    games_played: int = 0
    
    # Season averages
    season_spg: Optional[float] = Field(None, description="Steals per game")
    season_bpg: Optional[float] = Field(None, description="Blocks per game")
    season_fg_pct: Optional[float] = None
    season_fg3_pct: Optional[float] = None
    season_ft_pct: Optional[float] = None
    season_mpg: Optional[float] = Field(None, description="Minutes per game")


# ============== Stats Schemas ==============

class GameStatsBase(BaseModel):
    """Base game stats schema."""
    game_date: date
    opponent_team: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    is_home: bool = False
    minutes: float = 0
    points: int = 0
    rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    fg_pct: float = 0
    fg3_pct: float = 0
    ft_pct: float = 0


class GameStats(GameStatsBase):
    """Game stats with ID."""
    id: int
    player_id: int
    
    class Config:
        from_attributes = True


class RecentPerformance(BaseModel):
    """Recent performance data for charts."""
    games: List[GameStats]
    rolling_avg_5: Optional[dict] = None
    rolling_avg_10: Optional[dict] = None


# ============== Prediction Schemas ==============

class PredictionBase(BaseModel):
    """Base prediction schema."""
    game_date: date
    opponent_team: Optional[str] = None
    is_home: bool = False


class PredictionResult(PredictionBase):
    """Prediction result with confidence intervals."""
    player_id: int
    player_name: Optional[str] = None
    
    # Predictions
    predicted_points: float
    predicted_rebounds: float
    predicted_assists: float
    
    # Confidence intervals
    points_lower: float
    points_upper: float
    rebounds_lower: float
    rebounds_upper: float
    assists_lower: float
    assists_upper: float
    
    # Fantasy score estimate
    fantasy_score: Optional[float] = Field(None, description="Estimated fantasy points")
    
    class Config:
        from_attributes = True


class TopPerformer(BaseModel):
    """Top performer prediction."""
    player_id: int
    player_name: str
    team: Optional[str] = None
    team_abbreviation: Optional[str] = None
    position: Optional[str] = None
    headshot_url: Optional[str] = None
    
    predicted_points: float
    predicted_rebounds: float
    predicted_assists: float
    fantasy_score: float
    
    opponent_team: Optional[str] = None
    is_home: bool = False


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions."""
    player_ids: List[int]
    game_date: Optional[date] = None


class BatchPredictionResponse(BaseModel):
    """Response for batch predictions."""
    predictions: List[PredictionResult]
    generated_at: datetime


# ============== Model Metrics Schemas ==============

class ModelMetrics(BaseModel):
    """ML model evaluation metrics."""
    model_config = {"protected_namespaces": ()}
    
    model_name: str
    mae: float = Field(..., description="Mean Absolute Error")
    rmse: float = Field(..., description="Root Mean Square Error")
    r2: float = Field(..., description="R-squared score")
    last_trained: Optional[datetime] = None
    training_samples: int = 0


class AllModelMetrics(BaseModel):
    """All model metrics."""
    points_model: ModelMetrics
    rebounds_model: ModelMetrics
    assists_model: ModelMetrics


# ============== API Response Schemas ==============

class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List
    total: int
    page: int
    per_page: int
    pages: int


class PlayerSearchResult(BaseModel):
    """Player search result."""
    id: int
    nba_id: int
    name: str
    team: Optional[str] = None
    team_abbreviation: Optional[str] = None
    position: Optional[str] = None
    headshot_url: Optional[str] = None
