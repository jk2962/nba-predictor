"""
Comprehensive Player Metadata Collection Script.
Fetches complete player info from NBA API including:
- Team
- Position  
- Height/Weight
- Headshot URLs

Then syncs to SQLite database with proper shooting percentages.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import logging
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import NBA API
try:
    from nba_api.stats.static import players as nba_players
    from nba_api.stats.endpoints import commonplayerinfo
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    logger.warning("nba_api not available - will use CSV data only")


def fetch_player_metadata(player_id: int) -> dict:
    """Fetch complete player metadata from NBA API."""
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        data = info.get_normalized_dict()
        
        if data.get('CommonPlayerInfo'):
            player_info = data['CommonPlayerInfo'][0]
            return {
                'team': player_info.get('TEAM_NAME', ''),
                'team_abbreviation': player_info.get('TEAM_ABBREVIATION', ''),
                'position': player_info.get('POSITION', ''),
                'height': player_info.get('HEIGHT', ''),
                'weight': player_info.get('WEIGHT', ''),
                'headshot_url': f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
            }
    except Exception as e:
        logger.debug(f"Could not fetch metadata for {player_id}: {e}")
    
    return {
        'team': '',
        'team_abbreviation': '',
        'position': '',
        'height': '',
        'weight': '',
        'headshot_url': f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
    }


def sync_complete_database():
    """Sync CSV data to database with complete metadata."""
    
    csv_path = Path('data/full_nba_game_logs.csv')
    db_path = Path('data/nba.db')
    
    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return
        
    logger.info("="*70)
    logger.info("SYNCING COMPLETE PLAYER DATA TO DATABASE")
    logger.info("="*70)
    
    # Load CSV
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df):,} game logs for {df['player_id'].nunique()} players")
    
    # Get unique players
    unique_players = df[['player_id', 'player_name']].drop_duplicates()
    logger.info(f"Found {len(unique_players)} unique players")
    
    # Calculate career shooting stats per player from game logs
    logger.info("\n[CALCULATING SHOOTING STATS]")
    
    player_stats = df.groupby('player_id').agg({
        'field_goals_made': 'sum',
        'field_goal_attempts': 'sum',
        'three_pointers_made': 'sum',
        'three_point_attempts': 'sum',
        'free_throws_made': 'sum',
        'free_throw_attempts': 'sum',
    }).reset_index()
    
    player_stats['fg_pct'] = (player_stats['field_goals_made'] / player_stats['field_goal_attempts'].replace(0, 1)).round(3)
    player_stats['fg3_pct'] = (player_stats['three_pointers_made'] / player_stats['three_point_attempts'].replace(0, 1)).round(3)
    player_stats['ft_pct'] = (player_stats['free_throws_made'] / player_stats['free_throw_attempts'].replace(0, 1)).round(3)
    
    # Fetch player metadata from NBA API
    logger.info("\n[FETCHING PLAYER METADATA FROM NBA API]")
    
    player_metadata = {}
    total = len(unique_players)
    
    for idx, row in unique_players.iterrows():
        player_id = row['player_id']
        player_name = row['player_name']
        
        if NBA_API_AVAILABLE and player_id < 10000000:  # Skip fake IDs (2025 rookies)
            metadata = fetch_player_metadata(player_id)
            time.sleep(0.6)  # Rate limiting
        else:
            # Use defaults for rookies or if API unavailable
            metadata = {
                'team': 'TBD',
                'team_abbreviation': 'TBD',
                'position': 'F',
                'height': '6-6',
                'weight': '200',
                'headshot_url': f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
            }
        
        player_metadata[player_id] = metadata
        
        if (idx + 1) % 50 == 0:
            logger.info(f"  Processed {idx + 1}/{total} players...")
    
    logger.info(f"  Fetched metadata for {len(player_metadata)} players")
    
    # Build complete players DataFrame
    logger.info("\n[BUILDING PLAYERS TABLE]")
    
    players_data = []
    for idx, (_, row) in enumerate(unique_players.iterrows()):
        player_id = row['player_id']
        player_name = row['player_name']
        meta = player_metadata.get(player_id, {})
        stats = player_stats[player_stats['player_id'] == player_id]
        
        players_data.append({
            'id': idx + 1,
            'nba_id': player_id,
            'name': player_name,
            'team': meta.get('team', ''),
            'team_abbreviation': meta.get('team_abbreviation', ''),
            'position': meta.get('position', ''),
            'height': meta.get('height', ''),
            'weight': meta.get('weight', ''),
            'headshot_url': meta.get('headshot_url', ''),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        })
    
    players_df = pd.DataFrame(players_data)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Save players
    cursor.execute("DROP TABLE IF EXISTS players")
    players_df.to_sql('players', conn, index=False, if_exists='replace')
    logger.info(f"  Created players table with {len(players_df)} players")
    
    # Build games table
    logger.info("\n[BUILDING GAMES TABLE]")
    
    games_df = df[['game_date', 'matchup', 'season']].drop_duplicates()
    games_data = []
    for idx, (_, row) in enumerate(games_df.iterrows()):
        games_data.append({
            'id': idx + 1,
            'nba_game_id': f"G{idx + 1}",
            'game_date': row['game_date'],
            'home_team': '',
            'home_team_abbreviation': '',
            'away_team': '',
            'away_team_abbreviation': '',
            'season': row['season'],
        })
    
    games_df_final = pd.DataFrame(games_data)
    cursor.execute("DROP TABLE IF EXISTS games")
    games_df_final.to_sql('games', conn, index=False, if_exists='replace')
    logger.info(f"  Created games table with {len(games_df_final)} games")
    
    # Build player_stats with proper shooting %
    logger.info("\n[BUILDING PLAYER_STATS TABLE]")
    
    # Create ID mappings
    player_id_map = dict(zip(players_df['nba_id'], players_df['id']))
    game_key_map = {(r['game_date'], r['season']): r['id'] for _, r in games_df_final.iterrows()}
    
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
            'opponent_team': row.get('opponent', ''),
            'opponent_abbreviation': '',
            'rest_days': 0,
            'minutes': row.get('minutes', 0),
            'points': row.get('points', 0),
            'rebounds': row.get('rebounds', 0),
            'assists': row.get('assists', 0),
            'steals': row.get('steals', 0),
            'blocks': row.get('blocks', 0),
            'turnovers': row.get('turnovers', 0),
            'fg_made': row.get('field_goals_made', 0),
            'fg_attempted': row.get('field_goal_attempts', 0),
            'fg_pct': row.get('field_goal_pct', 0),
            'fg3_made': row.get('three_pointers_made', 0),
            'fg3_attempted': row.get('three_point_attempts', 0),
            'fg3_pct': row.get('three_point_pct', 0),
            'ft_made': row.get('free_throws_made', 0),
            'ft_attempted': row.get('free_throw_attempts', 0),
            'ft_pct': row.get('free_throw_pct', 0),
            'plus_minus': row.get('plus_minus', 0),
        })
    
    stats_df = pd.DataFrame(stats_rows)
    cursor.execute("DROP TABLE IF EXISTS player_stats")
    stats_df.to_sql('player_stats', conn, index=False, if_exists='replace')
    logger.info(f"  Created player_stats table with {len(stats_df):,} rows")
    
    conn.commit()
    conn.close()
    
    # Print sample to verify
    logger.info("\n[SAMPLE DATA VERIFICATION]")
    sample_player = players_df[players_df['name'] == 'LeBron James']
    if not sample_player.empty:
        p = sample_player.iloc[0]
        logger.info(f"  LeBron James:")
        logger.info(f"    Team: {p['team']}")
        logger.info(f"    Position: {p['position']}")
        logger.info(f"    Height: {p['height']}")
        logger.info(f"    Weight: {p['weight']}")
        logger.info(f"    Headshot: {p['headshot_url'][:50]}...")
    
    logger.info("\n" + "="*70)
    logger.info("SYNC COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    sync_complete_database()
