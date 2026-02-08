"""
Player Comparison Tool - Backend Engine
Compares 2-3 players using existing predictor infrastructure.

Usage:
    from scripts.player_comparison_simple import compare_players_cli
    
    compare_players_cli(['Trae Young', 'Luka Doncic'])
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from typing import List,Dict
from app.ml.predictor import SafePerformancePredictor
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def compare_players_cli(player_names: List[str], data_path: str = 'data/full_nba_game_logs.csv'):
    """
    Compare 2-3 players using the existing predictor.
    
    This is a simplified version that works with the actual ML infrastructure.
    """
    
    if len(player_names) < 2 or len(player_names) > 3:
        logger.error("Need 2-3 players to compare")
        return
    
    # Load predictor
    predictor = SafePerformancePredictor()
    predictor.load_models()
    
    # Load data
    df = pd.read_csv(data_path)
    df['game_date'] = pd.to_datetime(df['game_date'])
    df = df.sort_values(['player_id', 'game_date'])
    
    logger.info("="*90)
    logger.info(" " * 30 + "PLAYER COMPARISON")
    logger.info("="*90)
    logger.info("")
    
    comparison_data = {}
    
    for player_name in player_names:
        # Find player games
        player_games = df[df['player_name'].str.lower() == player_name.lower()]
        
        if len(player_games) == 0:
            logger.warning(f"Player '{player_name}' not found")
            continue
        
        # Get recent stats
        last_5 = player_games.tail(5)
        season_stats = player_games
        
        # Get latest game for prediction context
        latest_game = player_games.iloc[-1]
        
        # Make predictions
        try:
            predictions = predictor.predict(
                player_games,
                player_position=latest_game.get('position', 'G'),
                is_home=int(latest_game.get('is_home', 1)),
                opponent_def_rating=float(latest_game.get('opponent_def_rating', 110.0)),
                rest_days=int(latest_game.get('rest_days', 2))
            )
        except Exception as e:
            logger.error(f"Prediction failed for {player_name}: {e}")
            predictions = {}
        
        comparison_data[player_name] = {
            'predictions': predictions,
            'season_avg': {
                'points': round(season_stats['points'].mean(), 1),
                'rebounds': round(season_stats['rebounds'].mean(), 1),
                'assists': round(season_stats['assists'].mean(), 1),
            },
            'last_5_avg': {
                'points': round(last_5['points'].mean(), 1),
                'rebounds': round(last_5['rebounds'].mean(), 1),
                'assists': round(last_5['assists'].mean(), 1),
            },
            'games_played': len(player_games),
            'latest': latest_game
        }
    
    # Format output
    header = f"{'Category':<20}"
    for player in comparison_data.keys():
        header += f"{player[:22]:^23}"
    logger.info(header)
    logger.info("-" * 90)
    
    # Opponent
    row = f"{'Opponent':<20}"
    for player, data in comparison_data.items():
        opp = data['latest'].get('opponent', 'N/A')
        row += f"{opp:^23}"
    logger.info(row)
    
    # Location
    row = f"{'Location':<20}"
    for player, data in comparison_data.items():
        loc = 'Home' if data['latest'].get('is_home', 1) == 1 else 'Away'
        row += f"{loc:^23}"
    logger.info(row)
    
    logger.info("")
    logger.info("-" * 90)
    logger.info(" " * 30 + "NEXT GAME PREDICTIONS")
    logger.info("-" * 90)
    
    # Predictions
    for stat in ['points', 'rebounds', 'assists']:
        row = f"{stat.capitalize():<20}"
        
        for player, data in comparison_data.items():
            pred = data['predictions'].get(stat, 'N/A')
            if isinstance(pred, (int, float)):
                row += f"{pred:.1f}:^23"
            else:
                row += f"{'N/A':^23}"
        
        logger.info(row)
    
    logger.info("")
    logger.info("-" * 90)
    logger.info(" " * 30 + "SEASON AVERAGES")
    logger.info("-" * 90)
    
    for stat in ['points', 'rebounds', 'assists']:
        row = f"{stat.capitalize():<20}"
        
        for player, data in comparison_data.items():
            avg = data['season_avg'][stat]
            row += f"{avg:.1f}:^23"
        
        logger.info(row)
    
    logger.info("")
    logger.info("-" * 90)
    logger.info(" " * 30 + "RECENT FORM (Last 5)")
    logger.info("-" * 90)
    
    for stat in ['points', 'rebounds', 'assists']:
        row = f"{stat.capitalize():<20}"
        
        for player, data in comparison_data.items():
            avg = data['last_5_avg'][stat]
            row += f"{avg:.1f}:^23"
        
        logger.info(row)
    
    logger.info("")
    logger.info("=" * 90)


if __name__ == "__main__":
    # Test
    compare_players_cli(['Trae Young', 'Luka Doncic'])
    
    print("\n\n")
    
    compare_players_cli(['Stephen Curry', 'Damian Lillard', 'Kyrie Irving'])
