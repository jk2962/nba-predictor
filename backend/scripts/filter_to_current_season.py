"""
Filter dataset to ONLY 2025-26 season.
Removes all historical data and players who haven't played this season.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def filter_to_current_season():
    """Filter dataset to only include 2025-26 season games."""
    
    logger.info("="*80)
    logger.info("FILTERING TO 2025-26 SEASON ONLY")
    logger.info("="*80)
    
    # Load full dataset
    df = pd.read_csv('data/full_nba_game_logs.csv')
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    logger.info(f"\nOriginal dataset:")
    logger.info(f"  Total players: {df['player_id'].nunique()}")
    logger.info(f"  Total games: {len(df):,}")
    logger.info(f"  Date range: {df['game_date'].min().date()} to {df['game_date'].max().date()}")
    
    # Show season breakdown
    if 'season' in df.columns:
        logger.info(f"\nGames by season:")
        for season, count in df['season'].value_counts().sort_index().items():
            logger.info(f"  {season}: {count:,} games")
    
    # Filter to 2025-26 season only (using season column)
    logger.info(f"\n{'='*80}")
    logger.info(f"FILTERING TO 2025-26 SEASON")
    logger.info(f"{'='*80}")
    
    df_current = df[df['season'] == '2025-26'].copy()
    
    # Get players in current season
    current_season_players = df_current['player_name'].unique()
    removed_players = set(df['player_name'].unique()) - set(current_season_players)
    
    logger.info(f"\nFiltering results:")
    logger.info(f"  Original: {len(df):,} games from {df['player_id'].nunique()} players")
    logger.info(f"  Filtered: {len(df_current):,} games from {df_current['player_id'].nunique()} players")
    logger.info(f"  Removed: {len(removed_players)} players not active in 2025-26")
    
    # Check specific players
    logger.info(f"\n{'='*80}")
    logger.info(f"PLAYER VERIFICATION")
    logger.info(f"{'='*80}")
    
    test_cases = [
        'Jayson Tatum',
        'LeBron James',
        'Victor Wembanyama',
        'Stephen Curry',
        'Nikola Jokic',
        'Ace Bailey',
    ]
    
    for player_name in test_cases:
        in_original = player_name in df['player_name'].values
        in_filtered = player_name in current_season_players
        
        if in_original and not in_filtered:
            last_game = df[df['player_name'] == player_name]['game_date'].max()
            days_ago = (datetime.now() - last_game).days
            logger.info(f"✗ {player_name:25} REMOVED (last game: {last_game.date()}, {days_ago}d ago)")
        elif in_filtered:
            games = len(df_current[df_current['player_name'] == player_name])
            logger.info(f"✓ {player_name:25} INCLUDED ({games} games this season)")
        else:
            logger.info(f"? {player_name:25} NOT IN DATASET")
    
    # Show removed high-profile players
    if removed_players:
        logger.info(f"\n{'='*80}")
        logger.info(f"SAMPLE REMOVED PLAYERS (first 15)")
        logger.info(f"{'='*80}")
        
        removed_with_dates = []
        for player in removed_players:
            last_game = df[df['player_name'] == player]['game_date'].max()
            days_ago = (datetime.now() - last_game).days
            removed_with_dates.append((player, last_game, days_ago))
        
        removed_with_dates.sort(key=lambda x: x[2])  # Sort by recency
        
        for player, last_game, days_ago in removed_with_dates[:15]:
            logger.info(f"  {player:30} Last: {last_game.date()}, {days_ago:3}d ago")
    
    # Backup original
    backup_file = Path('data/full_nba_game_logs_ALL_SEASONS.csv')
    if not backup_file.exists():
        df.to_csv(backup_file, index=False)
        logger.info(f"\n✓ Backup saved to: {backup_file}")
    
    # Save filtered dataset (overwrite main file)
    df_current.to_csv('data/full_nba_game_logs.csv', index=False)
    logger.info(f"✓ Updated data/full_nba_game_logs.csv to 2025-26 only")
    
    # Save current season copy
    df_current.to_csv('data/current_season_game_logs.csv', index=False)
    logger.info(f"✓ Saved data/current_season_game_logs.csv")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"FILTERING COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Players: {df_current['player_id'].nunique()}")
    logger.info(f"Games: {len(df_current):,}")
    logger.info(f"Date range: {df_current['game_date'].min().date()} to {df_current['game_date'].max().date()}")
    
    return df_current, removed_players


if __name__ == "__main__":
    filter_to_current_season()
