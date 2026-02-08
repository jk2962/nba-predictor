"""
NBA Player Performance Prediction - Database Models
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Player(Base):
    """NBA Player model."""
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    nba_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, index=True)
    team = Column(String(50))
    team_abbreviation = Column(String(10))
    position = Column(String(20))
    height = Column(String(10))
    weight = Column(String(10))
    headshot_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stats = relationship("PlayerStats", back_populates="player", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="player", cascade="all, delete-orphan")


class Game(Base):
    """Game model."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    nba_game_id = Column(String(20), unique=True, index=True)
    game_date = Column(Date, nullable=False, index=True)
    home_team = Column(String(50))
    home_team_abbreviation = Column(String(10))
    away_team = Column(String(50))
    away_team_abbreviation = Column(String(10))
    season = Column(String(10))  # e.g., "2023-24"
    
    # Relationships
    stats = relationship("PlayerStats", back_populates="game", cascade="all, delete-orphan")


class PlayerStats(Base):
    """Player game statistics model."""
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    
    # Game context
    is_home = Column(Boolean)
    opponent_team = Column(String(50))
    opponent_abbreviation = Column(String(10))
    rest_days = Column(Integer, default=0)
    
    # Core stats
    minutes = Column(Float, default=0)
    points = Column(Integer, default=0)
    rebounds = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    steals = Column(Integer, default=0)
    blocks = Column(Integer, default=0)
    turnovers = Column(Integer, default=0)
    
    # Shooting percentages
    fg_made = Column(Integer, default=0)
    fg_attempted = Column(Integer, default=0)
    fg_pct = Column(Float, default=0)
    fg3_made = Column(Integer, default=0)
    fg3_attempted = Column(Integer, default=0)
    fg3_pct = Column(Float, default=0)
    ft_made = Column(Integer, default=0)
    ft_attempted = Column(Integer, default=0)
    ft_pct = Column(Float, default=0)
    
    # Plus/minus
    plus_minus = Column(Integer, default=0)
    
    # Relationships
    player = relationship("Player", back_populates="stats")
    game = relationship("Game", back_populates="stats")


class Prediction(Base):
    """Player performance prediction model."""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    
    # Prediction target
    game_date = Column(Date, nullable=False, index=True)
    opponent_team = Column(String(50))
    is_home = Column(Boolean)
    
    # Predicted values
    predicted_points = Column(Float)
    predicted_rebounds = Column(Float)
    predicted_assists = Column(Float)
    
    # Confidence intervals
    points_lower = Column(Float)
    points_upper = Column(Float)
    rebounds_lower = Column(Float)
    rebounds_upper = Column(Float)
    assists_lower = Column(Float)
    assists_upper = Column(Float)
    
    # Model metadata
    model_version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="predictions")
