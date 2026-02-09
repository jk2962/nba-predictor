"""
NBA Player Performance Prediction - Player Stats Service
"""
from typing import Optional, List, Tuple, Literal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
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
        active_only: bool = True,
        # Stat range filters
        ppg_min: Optional[float] = None,
        ppg_max: Optional[float] = None,
        rpg_min: Optional[float] = None,
        rpg_max: Optional[float] = None,
        apg_min: Optional[float] = None,
        apg_max: Optional[float] = None,
        mpg_min: Optional[float] = None,
        mpg_max: Optional[float] = None,
        # Sorting
        sort_by: Literal['name', 'ppg', 'rpg', 'apg', 'mpg', 'fantasy'] = 'name',
        sort_order: Literal['asc', 'desc'] = 'asc',
    ) -> Tuple[List[dict], int]:
        """
        Get paginated list of players with optional filters and sorting.
        
        Now returns dict with stats included, not just Player objects.
        
        Returns:
            Tuple of (players list with stats, total count)
        """
        query = db.query(Player)
        
        if active_only:
            query = query.filter(Player.is_active == True)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Player.name.ilike(search_term)) |
                (Player.team.ilike(search_term)) |
                (Player.team_abbreviation.ilike(search_term))
            )
        
        if position:
            # Support multiple positions (comma-separated)
            positions = [p.strip().upper() for p in position.split(',')]
            position_filters = []
            for pos in positions:
                position_filters.append(Player.position.ilike(f"{pos}%"))
            if position_filters:
                from sqlalchemy import or_
                query = query.filter(or_(*position_filters))
        
        if team:
            # Support multiple teams (comma-separated)
            teams = [t.strip().upper() for t in team.split(',')]
            team_filters = []
            for t in teams:
                team_filters.append(Player.team_abbreviation.ilike(t))
            if team_filters:
                from sqlalchemy import or_
                query = query.filter(or_(*team_filters))
        
        # Get all matching players first
        all_players = query.all()
        
        # Calculate stats for each player and apply stat filters
        players_with_stats = []
        for player in all_players:
            stats = PlayerService.get_player_season_stats(db, player.id)
            
            if not stats.get('games_played', 0):
                continue
            
            ppg = stats.get('ppg', 0) or 0
            rpg = stats.get('rpg', 0) or 0
            apg = stats.get('apg', 0) or 0
            mpg = stats.get('mpg', 0) or 0
            spg = stats.get('spg', 0) or 0
            bpg = stats.get('bpg', 0) or 0
            topg = stats.get('topg', 0) or 0
            
            # Apply stat filters
            if ppg_min is not None and ppg < ppg_min:
                continue
            if ppg_max is not None and ppg > ppg_max:
                continue
            if rpg_min is not None and rpg < rpg_min:
                continue
            if rpg_max is not None and rpg > rpg_max:
                continue
            if apg_min is not None and apg < apg_min:
                continue
            if apg_max is not None and apg > apg_max:
                continue
            if mpg_min is not None and mpg < mpg_min:
                continue
            if mpg_max is not None and mpg > mpg_max:
                continue
            
            # Calculate fantasy score: PTS + 1.2*REB + 1.5*AST + 3*STL + 3*BLK - 1*TOV
            fantasy = ppg + 1.2 * rpg + 1.5 * apg + 3.0 * spg + 3.0 * bpg - 1.0 * topg
            
            players_with_stats.append({
                'player': player,
                'ppg': ppg,
                'rpg': rpg,
                'apg': apg,
                'mpg': mpg,
                'spg': spg,
                'bpg': bpg,
                'fantasy': round(fantasy, 1),
                'games_played': stats.get('games_played', 0),
                'fg_pct': stats.get('fg_pct', 0),
                'fg3_pct': stats.get('fg3_pct', 0),
                'ft_pct': stats.get('ft_pct', 0),
            })
        
        # Sort
        sort_key = sort_by if sort_by in ['ppg', 'rpg', 'apg', 'mpg', 'fantasy'] else 'player'
        if sort_key == 'player':
            players_with_stats.sort(
                key=lambda x: x['player'].name.lower(),
                reverse=(sort_order == 'desc')
            )
        else:
            players_with_stats.sort(
                key=lambda x: x[sort_key],
                reverse=(sort_order == 'desc')
            )
        
        total = len(players_with_stats)
        
        # Apply pagination
        paginated = players_with_stats[skip:skip + limit]
        
        return paginated, total
    
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
            func.avg(PlayerStats.turnovers).label('topg'),
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
            'topg': round(result.topg, 1) if result.topg else 0,
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
    
    @staticmethod
    def get_all_teams(db: Session) -> List[dict]:
        """Get list of all unique teams."""
        teams = (
            db.query(Player.team, Player.team_abbreviation)
            .filter(Player.is_active == True)
            .distinct()
            .all()
        )
        return [
            {'name': t[0], 'abbreviation': t[1]} 
            for t in teams if t[0] and t[1]
        ]

