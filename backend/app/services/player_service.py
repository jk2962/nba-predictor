"""
NBA Player Performance Prediction - Player Stats Service
"""
from typing import Optional, List, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import pandas as pd
from app.models import Player, Game, PlayerStats, Prediction
from app.schemas import PlayerListItem, PlayerDetail, GameStats, PredictionResult


class PlayerService:
    """Service for player-related operations."""
    
    @staticmethod
    def get_players(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        position: Optional[str] = None,
        team: Optional[str] = None,
        active_only: bool = True
    ) -> Tuple[List[Player], int]:
        """
        Get paginated list of players with optional filters.
        
        Returns:
            Tuple of (players list, total count)
        """
        query = db.query(Player)
        
        if active_only:
            query = query.filter(Player.is_active == True)
        
        if search:
            query = query.filter(Player.name.ilike(f"%{search}%"))
        
        if position:
            query = query.filter(Player.position.ilike(f"%{position}%"))
        
        if team:
            query = query.filter(
                (Player.team.ilike(f"%{team}%")) | 
                (Player.team_abbreviation.ilike(f"%{team}%"))
            )
        
        total = query.count()
        players = query.order_by(Player.name).offset(skip).limit(limit).all()
        
        return players, total
    
    @staticmethod
    def get_player_by_id(db: Session, player_id: int) -> Optional[Player]:
        """Get a player by ID."""
        return db.query(Player).filter(Player.id == player_id).first()
    
    @staticmethod
    def get_player_by_nba_id(db: Session, nba_id: int) -> Optional[Player]:
        """Get a player by NBA ID."""
        return db.query(Player).filter(Player.nba_id == nba_id).first()
    
    @staticmethod
    def get_player_season_stats(
        db: Session,
        player_id: int,
        season: Optional[str] = None
    ) -> dict:
        """
        Calculate season averages for a player.
        
        Returns:
            Dictionary with season averages
        """
        query = db.query(
            func.count(PlayerStats.id).label('games_played'),
            func.avg(PlayerStats.points).label('ppg'),
            func.avg(PlayerStats.rebounds).label('rpg'),
            func.avg(PlayerStats.assists).label('apg'),
            func.avg(PlayerStats.steals).label('spg'),
            func.avg(PlayerStats.blocks).label('bpg'),
            func.avg(PlayerStats.minutes).label('mpg'),
            func.avg(PlayerStats.fg_pct).label('fg_pct'),
            func.avg(PlayerStats.fg3_pct).label('fg3_pct'),
            func.avg(PlayerStats.ft_pct).label('ft_pct'),
        ).join(Game).filter(PlayerStats.player_id == player_id)
        
        if season:
            query = query.filter(Game.season == season)
        
        result = query.first()
        
        if not result or result.games_played == 0:
            return {}
        
        return {
            'games_played': result.games_played,
            'ppg': round(result.ppg, 1) if result.ppg else 0,
            'rpg': round(result.rpg, 1) if result.rpg else 0,
            'apg': round(result.apg, 1) if result.apg else 0,
            'spg': round(result.spg, 1) if result.spg else 0,
            'bpg': round(result.bpg, 1) if result.bpg else 0,
            'mpg': round(result.mpg, 1) if result.mpg else 0,
            'fg_pct': round(result.fg_pct * 100, 1) if result.fg_pct else 0,
            'fg3_pct': round(result.fg3_pct * 100, 1) if result.fg3_pct else 0,
            'ft_pct': round(result.ft_pct * 100, 1) if result.ft_pct else 0,
        }
    
    @staticmethod
    def get_player_recent_games(
        db: Session,
        player_id: int,
        limit: int = 10
    ) -> List[PlayerStats]:
        """Get a player's most recent games."""
        return (
            db.query(PlayerStats)
            .join(Game)
            .filter(PlayerStats.player_id == player_id)
            .order_by(desc(Game.game_date))
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_player_stats_dataframe(
        db: Session,
        player_id: int,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get player stats as a pandas DataFrame for ML predictions.
        """
        query = (
            db.query(
                PlayerStats,
                Game.game_date,
                Game.season
            )
            .join(Game)
            .filter(PlayerStats.player_id == player_id)
            .order_by(Game.game_date)
        )
        
        if limit:
            query = query.limit(limit)
        
        results = query.all()
        
        if not results:
            return pd.DataFrame()
        
        data = []
        for stats, game_date, season in results:
            data.append({
                'game_date': game_date,
                'season': season,
                'is_home': stats.is_home,
                'opponent_team': stats.opponent_team,
                'rest_days': stats.rest_days or 1,
                'minutes': stats.minutes,
                'points': stats.points,
                'rebounds': stats.rebounds,
                'assists': stats.assists,
                'steals': stats.steals,
                'blocks': stats.blocks,
                'turnovers': stats.turnovers,
                'fg_pct': stats.fg_pct,
                'fg3_pct': stats.fg3_pct,
                'ft_pct': stats.ft_pct,
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def get_all_players_for_ranking(
        db: Session,
        position: Optional[str] = None
    ) -> List[dict]:
        """
        Get all active players with their season stats for draft ranking.
        """
        query = db.query(Player).filter(Player.is_active == True)
        
        if position:
            query = query.filter(Player.position.ilike(f"%{position}%"))
        
        players = query.all()
        
        result = []
        for player in players:
            stats = PlayerService.get_player_season_stats(db, player.id)
            if stats.get('games_played', 0) > 0:
                result.append({
                    'id': player.id,
                    'nba_id': player.nba_id,
                    'name': player.name,
                    'team': player.team,
                    'team_abbreviation': player.team_abbreviation,
                    'position': player.position,
                    'headshot_url': player.headshot_url,
                    **stats
                })
        
        return result
