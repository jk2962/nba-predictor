"""
Fantasy Basketball Draft Helper
Ranks players by projected fantasy value and provides draft recommendations.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import joblib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DraftHelper:
    """
    Fantasy basketball draft assistant.
    
    Features:
    - Player rankings by projected fantasy value
    - Value Over Replacement (VOR) calculation
    - Positional scarcity analysis
    - Best Available Player (BAP) recommendations
    - Custom league scoring systems
    """
    
    def __init__(
        self, 
        models_dir: str = './models',
        data_path: str = './data/full_nba_game_logs.csv'
    ):
        self.models_dir = Path(models_dir)
        self.data_path = data_path
        
        # Data cache
        self.projections = None
        self.games_played_cache = {}
        
        # Load player data and settings
        self.load_data()
        
    def load_player_activity_stats(self) -> pd.DataFrame:
        """Load player activity statistics"""
        activity_file = Path('data/player_activity_stats.csv')
        
        if activity_file.exists():
            activity_stats = pd.read_csv(activity_file)
            logger.info(f"✓ Loaded activity stats for {len(activity_stats)} players")
            return activity_stats
        else:
            logger.warning("⚠️  No activity stats found - all players will be included")
            return pd.DataFrame()

    def load_data(self):
        """
        Load player data from CSV and initialize default settings.
        """
        self.player_data = self._load_player_data()
        
        # Default fantasy scoring weights (standard league)
        self.default_scoring = {
            'points': 1.0,
            'rebounds': 1.2,      # Slightly more valuable
            'assists': 1.5,       # Most valuable
            'steals': 3.0,        # Stocks highly valued
            'blocks': 3.0,
            'turnovers': -1.0     # Negative value
        }
        
        # League settings
        self.league_size = 12  # Standard 12-team league
        
    def _load_player_data(self) -> pd.DataFrame:
        """Load player game logs"""
        try:
            df = pd.read_csv(self.data_path)
            df['game_date'] = pd.to_datetime(df['game_date'], errors='coerce')
            logger.info(f"Loaded {df['player_id'].nunique()} players from dataset")
            return df
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return pd.DataFrame()
    
    def calculate_player_projections(
        self,
        use_predictions: bool = True,
        exclude_inactive: bool = True
    ) -> pd.DataFrame:
        """
        Calculate season projections for all players.
        
        Args:
            exclude_inactive: Filter out players inactive 6+ months
            
        Returns:
            DataFrame with player projections
        """
        
        logger.info("Calculating player projections...")
        
        # Get season averages for all players
        # Note: In a real app, this would use the ML models for forward-looking projections
        # Here we use season averages as the baseline projection
        projections = self.player_data.groupby('player_name').agg({
            'player_id': 'first',
            'points': 'mean',
            'rebounds': 'mean',
            'assists': 'mean',
            'steals': 'mean' if 'steals' in self.player_data.columns else lambda x: 0,
            'blocks': 'mean' if 'blocks' in self.player_data.columns else lambda x: 0,
            'turnovers': 'mean' if 'turnovers' in self.player_data.columns else lambda x: 0,
            'minutes': 'mean' if 'minutes' in self.player_data.columns else lambda x: 0,
        }).reset_index()
        
        # Rename columns
        projections.columns = [
            'player_name', 'player_id',
            'proj_points', 'proj_rebounds', 'proj_assists',
            'proj_steals', 'proj_blocks', 'proj_turnovers',
            'proj_minutes'
        ]
        
        # Add position as "ALL" for now (can be enhanced later)
        projections['position'] = 'ALL'
        
        # Round projections
        stat_cols = [col for col in projections.columns if col.startswith('proj_')]
        for col in stat_cols:
            projections[col] = projections[col].round(1)
        
        # Filter inactive players if requested
        if exclude_inactive:
            activity_stats = self.load_player_activity_stats()
            
            if not activity_stats.empty:
                # Get list of active player IDs
                active_ids = activity_stats[
                    activity_stats['is_active'] == True
                ]['player_id'].tolist()
                
                initial_count = len(projections)
                projections = projections[
                    projections['player_id'].isin(active_ids)
                ].copy()
                
                excluded_count = initial_count - len(projections)
                
                logger.info(f"Activity filtering: {initial_count} -> {len(projections)} players (Excluded {excluded_count} inactive)")
        
                logger.info(f"Activity filtering: {initial_count} -> {len(projections)} players (Excluded {excluded_count} inactive)")
                
                # Filter to players with meaningful minutes (>5 MPG)
                # Only apply this if we are excluding inactive (otherwise we want to see everyone)
                projections = projections[projections['proj_minutes'] > 5].copy()
                logger.info(f"Projected {len(projections)} active players with >5 MPG")
        
        return projections
    
    def calculate_fantasy_points(
        self,
        projections: pd.DataFrame,
        scoring_system: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Calculate fantasy points for each player.
        
        Args:
            projections: DataFrame with player projections
            scoring_system: Custom scoring (or use default)
        
        Returns:
            DataFrame with fantasy_points column added
        """
        
        if scoring_system is None:
            scoring_system = self.default_scoring
        
        logger.info(f"Calculating fantasy points with scoring: {scoring_system}")
        
        # Calculate fantasy points
        projections['fantasy_points'] = 0.0
        
        for stat, weight in scoring_system.items():
            col_name = f'proj_{stat}'
            if col_name in projections.columns:
                projections['fantasy_points'] += projections[col_name] * weight
        
        projections['fantasy_points'] = projections['fantasy_points'].round(1)
        
        return projections
    
    def calculate_value_over_replacement(
        self,
        projections: pd.DataFrame,
        league_size: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate Value Over Replacement (VOR).
        
        Since position data isn't available, we calculate a single
        replacement level based on the league size * roster spots.
        
        Args:
            projections: DataFrame with fantasy_points
            league_size: Number of teams in league (default: 12)
        
        Returns:
            DataFrame with VOR column added  
        """
        
        if league_size is None:
            league_size = self.league_size
        
        logger.info(f"Calculating VOR for {league_size}-team league")
        
        # Replacement level = the (league_size * 13)th player
        # Assumes 13-man rosters
        replacement_player_rank = league_size * 13
        
        sorted_players = projections.sort_values('fantasy_points', ascending=False)
        
        if len(sorted_players) >= replacement_player_rank:
            replacement_level = sorted_players.iloc[replacement_player_rank - 1]['fantasy_points']
        else:
            replacement_level = sorted_players['fantasy_points'].min()
        
        logger.info(f"  Replacement level: {replacement_level:.1f} fantasy points")
        
        # Calculate VOR for each player
        projections['vor'] = projections['fantasy_points'] - replacement_level
        projections['vor'] = projections['vor'].round(1)
        
        return projections
    
    def rank_all_players(
        self,
        scoring_system: Optional[Dict[str, float]] = None,
        league_size: Optional[int] = None,
        include_inactive: bool = False
    ) -> pd.DataFrame:
        """
        Generate complete player rankings.
        
        Args:
            scoring_system: Custom scoring weights
            league_size: Number of teams
            include_inactive: Include inactive players (default: False)
            
        Returns:
            DataFrame with all players ranked
        """
        
        logger.info("="*80)
        logger.info("GENERATING PLAYER RANKINGS")
        logger.info("="*80)
        
        # Get projections with activity filter
        # include_inactive=True -> exclude_inactive=False
        projections = self.calculate_player_projections(
            exclude_inactive=not include_inactive
        )
        
        # Calculate fantasy points
        projections = self.calculate_fantasy_points(projections, scoring_system)
        
        # Calculate VOR
        projections = self.calculate_value_over_replacement(projections, league_size)
        
        # Sort by fantasy points (descending)
        projections = projections.sort_values('fantasy_points', ascending=False)
        
        # Add overall rank
        projections['rank'] = range(1, len(projections) + 1)
        
        # Add positional rank
        projections['position_rank'] = projections.groupby('position')['fantasy_points'].rank(
            ascending=False, 
            method='dense'
        ).astype(int)
        
        # Reorder columns for readability
        column_order = [
            'rank', 'player_name', 'position', 'position_rank',
            'fantasy_points', 'vor',
            'proj_points', 'proj_rebounds', 'proj_assists',
            'proj_steals', 'proj_blocks', 'proj_turnovers',
            'proj_minutes'
        ]
        
        # Only include columns that exist
        column_order = [col for col in column_order if col in projections.columns]
        projections = projections[column_order]
        
        logger.info(f"Ranked {len(projections)} players")
        if len(projections) > 0:
            logger.info(f"  Top player: {projections.iloc[0]['player_name']} ({projections.iloc[0]['fantasy_points']:.1f} fpts)")
        
        return projections
    
    def get_best_available(
        self,
        rankings: pd.DataFrame,
        drafted_players: List[str],
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get best available players (not yet drafted).
        
        Args:
            rankings: Full player rankings
            drafted_players: List of already-drafted player names
            top_n: Number of players to return
        
        Returns:
            Top N available players
        """
        
        # Filter out drafted players
        available = rankings[~rankings['player_name'].isin(drafted_players)].copy()
        
        return available.head(top_n)
    
    def get_draft_recommendation(
        self,
        rankings: pd.DataFrame,
        drafted_players: List[str],
        my_team: Optional[List[str]] = None,
        team_needs: Optional[Dict[str, int]] = None
    ) -> Dict:
        """
        Get draft recommendation based on team needs and available players.
        
        Args:
            rankings: Full player rankings
            drafted_players: Already drafted players
            my_team: Players already on user's team
            team_needs: Positions still needed (e.g., {'G': 1, 'C': 2})
        
        Returns:
            Recommendation dictionary
        """
        
        if my_team is None:
            my_team = []
        
        # Get best available
        available = self.get_best_available(rankings, drafted_players, top_n=20)
        
        if len(available) == 0:
            return {'error': 'No players available'}
        
        # Simple recommendation: highest value available
        best_player = available.iloc[0]
        
        recommendation = {
            'recommended_player': best_player['player_name'],
            'rank': int(best_player['rank']),
            'position': best_player['position'],
            'fantasy_points': float(best_player['fantasy_points']),
            'vor': float(best_player['vor']),
            'reasoning': f"Highest value available (Rank #{best_player['rank']})"
        }
        
        # If team needs specified, adjust recommendation
        if team_needs:
            for position, count_needed in team_needs.items():
                if count_needed > 0:
                    pos_available = available[available['position'] == position]
                    
                    if len(pos_available) > 0:
                        best_for_need = pos_available.iloc[0]
                        
                        # If this player is in top 5 available, recommend them
                        if len(available) >= 5 and best_for_need['rank'] <= available.iloc[4]['rank']:
                            recommendation = {
                                'recommended_player': best_for_need['player_name'],
                                'rank': int(best_for_need['rank']),
                                'position': best_for_need['position'],
                                'fantasy_points': float(best_for_need['fantasy_points']),
                                'vor': float(best_for_need['vor']),
                                'reasoning': f"Fills {position} need + high value (Rank #{best_for_need['rank']})"
                            }
                            break
        
        # Add alternatives
        recommendation['alternatives'] = []
        for i in range(1, min(4, len(available))):
            alt = available.iloc[i]
            recommendation['alternatives'].append({
                'player_name': alt['player_name'],
                'rank': int(alt['rank']),
                'position': alt['position'],
                'fantasy_points': float(alt['fantasy_points'])
            })
        
        return recommendation
    
    def analyze_positional_scarcity(
        self,
        rankings: pd.DataFrame,
        drafted_players: List[str]
    ) -> Dict:
        """
        Analyze player scarcity (simplified version without positions).
        
        Returns:
            Scarcity analysis
        """
        
        available = rankings[~rankings['player_name'].isin(drafted_players)]
        
        # Simple overall scarcity
        if len(available) == 0:
            scarcity_data = {
                'remaining': 0,
                'avg_value': 0,
                'top_value': 0,
                'scarcity_level': 'CRITICAL'
            }
        else:
            top_20 = available.head(20)
            
            scarcity_data = {
                'remaining': len(available),
                'avg_value': float(top_20['fantasy_points'].mean().round(1)),
                'top_value': float(available.iloc[0]['fantasy_points'].round(1)),
                'scarcity_level': self._get_scarcity_level(len(available))
            }
        
        return {
            'ALL': scarcity_data
        }
    
    def _get_scarcity_level(self, remaining: int) -> str:
        """Determine scarcity level based on remaining players"""
        if remaining >= 30:
            return 'LOW'
        elif remaining >= 15:
            return 'MEDIUM'
        elif remaining >= 5:
            return 'HIGH'
        else:
            return 'CRITICAL'


# Singleton instance
_draft_helper_instance = None

def get_draft_helper() -> DraftHelper:
    """Get singleton draft helper instance"""
    global _draft_helper_instance
    
    if _draft_helper_instance is None:
        _draft_helper_instance = DraftHelper(
            models_dir='models',
            data_path='data/full_nba_game_logs.csv'
        )
    
    return _draft_helper_instance
