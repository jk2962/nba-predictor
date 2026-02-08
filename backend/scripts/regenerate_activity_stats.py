"""
Regenerate player_activity_stats.csv based on filtered 2025-26 season data.
Ensures draft helper uses only current season players.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def regenerate_activity_stats():
    """Regenerate activity stats for 2025-26 season players only."""
    
    logger.info("="*70)
    logger.info("REGENERATING ACTIVITY STATS FOR 2025-26 SEASON")
    logger.info("="*70)
    
    # Load current season data
    df = pd.read_csv('data/full_nba_game_logs.csv')
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    logger.info(f"\nDataset: {df['player_id'].nunique()} players, {len(df):,} games")
    logger.info(f"Date range: {df['game_date'].min().date()} to {df['game_date'].max().date()}")
    
    # Calculate stats per player
    player_stats = df.groupby(['player_id', 'player_name']).agg({
        'game_date': ['min', 'max', 'count'],
        'minutes': 'mean',
        'points': 'mean',
        'rebounds': 'mean',
        'assists': 'mean',
    }).reset_index()
    
    # Flatten column names
    player_stats.columns = [
        'player_id', 'player_name', 
        'first_game', 'last_game', 'games_played',
        'avg_minutes', 'avg_points', 'avg_rebounds', 'avg_assists'
    ]
    
    # Calculate days since last game
    today = datetime.now()
    player_stats['days_since_last_game'] = (today - player_stats['last_game']).dt.days
    
    # All 2025-26 players are considered active
    player_stats['is_active'] = True
    
    # Save
    output_file = Path('data/player_activity_stats.csv')
    player_stats.to_csv(output_file, index=False)
    
    logger.info(f"\n✓ Saved {len(player_stats)} players to {output_file}")
    logger.info(f"  All players marked as active (2025-26 season only)")
    
    # Sample output
    logger.info(f"\nSample players:")
    for _, row in player_stats.head(5).iterrows():
        logger.info(f"  {row['player_name']:25} {row['games_played']:3} games, {row['avg_points']:.1f} PPG")
    
    return player_stats


if __name__ == "__main__":
    regenerate_activity_stats()
