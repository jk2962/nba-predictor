"""
Sync CSV data to SQLite database.
Updates the main predictor database with the expanded dataset.
Matches SQLAlchemy schema for proper integration.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def sync_csv_to_database():
    """Sync the expanded CSV dataset to the SQLite database."""
    
    csv_path = Path('backend/data/full_nba_game_logs.csv')
    db_path = Path('backend/data/nba.db')
    
    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return
        
    logger.info("="*70)
    logger.info("SYNCING CSV DATA TO DATABASE (Schema-Compatible)")
    logger.info("="*70)
    
    # Load CSV
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df):,} game logs for {df['player_id'].nunique()} players")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update PLAYERS table (match SQLAlchemy schema)
    logger.info("\n[PLAYERS TABLE]")
    
    # Extract unique players
    player_cols = ['player_id', 'player_name']
    players_df = df[player_cols].drop_duplicates()
    
    # Build schema-compatible DataFrame
    players_schema = pd.DataFrame({
        'id': range(1, len(players_df) + 1),
        'nba_id': players_df['player_id'].values,
        'name': players_df['player_name'].values,
        'team': None,
        'team_abbreviation': None,
        'position': None,
        'height': None,
        'weight': None,
        'headshot_url': None,
        'is_active': True,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
    })
    
    # Drop existing and recreate
    cursor.execute("DROP TABLE IF EXISTS players")
    players_schema.to_sql('players', conn, index=False, if_exists='replace')
    logger.info(f"  Created players table with {len(players_schema)} players")
    
    # 2. Update GAMES table
    logger.info("\n[GAMES TABLE]")
    
    # Extract unique games
    games_df = df[['game_date', 'matchup', 'season']].drop_duplicates()
    games_schema = pd.DataFrame({
        'id': range(1, len(games_df) + 1),
        'nba_game_id': [f"G{i}" for i in range(1, len(games_df) + 1)],
        'game_date': games_df['game_date'].values,
        'home_team': None,
        'home_team_abbreviation': None,
        'away_team': None,
        'away_team_abbreviation': None,
        'season': games_df['season'].values,
    })
    
    cursor.execute("DROP TABLE IF EXISTS games")
    games_schema.to_sql('games', conn, index=False, if_exists='replace')
    logger.info(f"  Created games table with {len(games_schema)} games")
    
    # 3. Update PLAYER_STATS table
    logger.info("\n[PLAYER_STATS TABLE]")
    
    # Create player ID mapping (nba_id -> internal id)
    player_id_map = dict(zip(players_schema['nba_id'], players_schema['id']))
    
    # Create game ID mapping
    game_key_map = {}
    for idx, row in games_schema.iterrows():
        key = (row['game_date'], row['season'])
        game_key_map[key] = row['id']
    
    stats_rows = []
    for idx, row in df.iterrows():
        player_internal_id = player_id_map.get(row['player_id'])
        game_key = (row['game_date'], row.get('season', '2024-25'))
        game_internal_id = game_key_map.get(game_key, 1)
        
        stats_rows.append({
            'id': idx + 1,
            'player_id': player_internal_id,
            'game_id': game_internal_id,
            'is_home': row.get('home_game', False),
            'opponent_team': row.get('opponent', None),
            'opponent_abbreviation': None,
            'rest_days': 0,
            'minutes': row.get('minutes', 0),
            'points': row.get('points', 0),
            'rebounds': row.get('rebounds', 0),
            'assists': row.get('assists', 0),
            'steals': row.get('steals', 0),
            'blocks': row.get('blocks', 0),
            'turnovers': row.get('turnovers', 0),
            'fg_made': row.get('fgm', 0),
            'fg_attempted': row.get('fga', 0),
            'fg_pct': row.get('fg_pct', 0),
            'fg3_made': row.get('fg3m', 0),
            'fg3_attempted': row.get('fg3a', 0),
            'fg3_pct': row.get('fg3_pct', 0),
            'ft_made': row.get('ftm', 0),
            'ft_attempted': row.get('fta', 0),
            'ft_pct': row.get('ft_pct', 0),
            'plus_minus': row.get('plus_minus', 0),
        })
    
    stats_df = pd.DataFrame(stats_rows)
    cursor.execute("DROP TABLE IF EXISTS player_stats")
    stats_df.to_sql('player_stats', conn, index=False, if_exists='replace')
    logger.info(f"  Created player_stats table with {len(stats_df):,} rows")
    
    conn.commit()
    conn.close()
    
    logger.info("\n" + "="*70)
    logger.info("SYNC COMPLETE")
    logger.info("="*70)
    logger.info(f"Database: {db_path}")
    logger.info(f"Players: {len(players_schema)}")
    logger.info(f"Games: {len(games_schema)}")
    logger.info(f"Stats: {len(stats_df):,}")


if __name__ == "__main__":
    sync_csv_to_database()
