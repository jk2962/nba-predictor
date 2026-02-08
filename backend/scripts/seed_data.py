"""
NBA Player Performance Prediction - Data Seed Script

This script fetches NBA player data and historical stats using the nba_api library,
populates the database, and trains the ML models.

Usage:
    cd backend
    python -m scripts.seed_data

Note: This script is rate-limited by the NBA API and may take 10-15 minutes to complete.
"""
import sys
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, init_db
from app.models import Player, Game, PlayerStats
from app.ml import predictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# NBA API imports with delay to avoid rate limiting
try:
    from nba_api.stats.static import players as nba_players
    from nba_api.stats.static import teams as nba_teams
    from nba_api.stats.endpoints import playergamelog, commonplayerinfo
except ImportError:
    logger.error("nba_api not installed. Run: pip install nba_api")
    sys.exit(1)


# Top NBA players to seed (mix of positions and teams)
TOP_PLAYER_NAMES = [
    # Guards
    "Stephen Curry", "Luka Doncic", "Shai Gilgeous-Alexander", "Jaylen Brown",
    "Damian Lillard", "Tyrese Haliburton", "Trae Young", "Jalen Brunson",
    "Kyrie Irving", "De'Aaron Fox", "Anthony Edwards", "Donovan Mitchell",
    "Devin Booker", "LaMelo Ball", "Tyrese Maxey", "Cade Cunningham",
    
    # Forwards
    "LeBron James", "Kevin Durant", "Jayson Tatum", "Giannis Antetokounmpo",
    "Jimmy Butler", "Kawhi Leonard", "Paul George", "Pascal Siakam",
    "Brandon Ingram", "DeMar DeRozan", "Zion Williamson", "Paolo Banchero",
    "Scottie Barnes", "Domantas Sabonis", "Lauri Markkanen", "Franz Wagner",
    
    # Centers
    "Nikola Jokic", "Joel Embiid", "Anthony Davis", "Bam Adebayo",
    "Karl-Anthony Towns", "Rudy Gobert", "Jarrett Allen", "Evan Mobley",
    "Victor Wembanyama", "Chet Holmgren", "Brook Lopez", "Alperen Sengun",
    
    # Additional notable players
    "Ja Morant", "James Harden", "Chris Paul", "Jrue Holiday",
    "Mikal Bridges", "OG Anunoby", "Dejounte Murray", "Tyler Herro",
]


def get_nba_player_id(player_name: str) -> Optional[int]:
    """Get NBA player ID by name."""
    all_players = nba_players.get_players()
    for player in all_players:
        if player['full_name'].lower() == player_name.lower():
            return player['id']
    return None


def get_player_info(nba_id: int) -> Optional[dict]:
    """Get player common info from NBA API."""
    try:
        time.sleep(0.6)  # Rate limiting
        info = commonplayerinfo.CommonPlayerInfo(player_id=nba_id)
        data = info.get_data_frames()[0]
        
        if data.empty:
            return None
        
        row = data.iloc[0]
        return {
            'nba_id': nba_id,
            'name': row.get('DISPLAY_FIRST_LAST', ''),
            'team': row.get('TEAM_NAME', ''),
            'team_abbreviation': row.get('TEAM_ABBREVIATION', ''),
            'position': row.get('POSITION', ''),
            'height': row.get('HEIGHT', ''),
            'weight': row.get('WEIGHT', ''),
            'headshot_url': f"https://cdn.nba.com/headshots/nba/latest/1040x760/{nba_id}.png"
        }
    except Exception as e:
        logger.warning(f"Error getting player info for {nba_id}: {e}")
        return None


def get_player_game_logs(nba_id: int, seasons: List[str]) -> pd.DataFrame:
    """Get player game logs for specified seasons."""
    all_games = []
    
    for season in seasons:
        try:
            time.sleep(0.6)  # Rate limiting
            log = playergamelog.PlayerGameLog(
                player_id=nba_id,
                season=season,
                season_type_all_star='Regular Season'
            )
            df = log.get_data_frames()[0]
            
            if not df.empty:
                df['SEASON'] = season
                all_games.append(df)
                logger.debug(f"  Got {len(df)} games for season {season}")
                
        except Exception as e:
            logger.warning(f"Error getting game log for {nba_id} season {season}: {e}")
            continue
    
    if not all_games:
        return pd.DataFrame()
    
    return pd.concat(all_games, ignore_index=True)


def create_player(db: Session, player_info: dict) -> Player:
    """Create or update player in database."""
    existing = db.query(Player).filter(Player.nba_id == player_info['nba_id']).first()
    
    if existing:
        for key, value in player_info.items():
            setattr(existing, key, value)
        existing.is_active = True
        db.commit()
        return existing
    
    player = Player(**player_info, is_active=True)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def create_game(db: Session, game_data: dict) -> Game:
    """Create or get game in database."""
    existing = db.query(Game).filter(Game.nba_game_id == game_data['nba_game_id']).first()
    
    if existing:
        return existing
    
    game = Game(**game_data)
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def create_stats(db: Session, stats_data: dict) -> PlayerStats:
    """Create player stats entry."""
    stats = PlayerStats(**stats_data)
    db.add(stats)
    db.commit()
    return stats


def parse_game_log(row: pd.Series, player_id: int, db: Session, prev_game_date=None) -> Tuple[Game, dict]:
    """Parse a game log row and create game/stats entries."""
    # Parse game date
    game_date = pd.to_datetime(row['GAME_DATE']).date()
    
    # Parse matchup (e.g., "LAL vs. GSW" or "LAL @ GSW")
    matchup = row.get('MATCHUP', '')
    is_home = 'vs.' in matchup
    
    parts = matchup.replace('vs.', '@').split('@')
    if len(parts) == 2:
        team_abbr = parts[0].strip()
        opponent_abbr = parts[1].strip()
    else:
        team_abbr = ''
        opponent_abbr = ''
    
    # Calculate rest days
    rest_days = 1
    if prev_game_date:
        rest_days = (game_date - prev_game_date).days
    
    # Create game entry
    game_data = {
        'nba_game_id': str(row.get('Game_ID', '')),
        'game_date': game_date,
        'home_team': team_abbr if is_home else opponent_abbr,
        'home_team_abbreviation': team_abbr if is_home else opponent_abbr,
        'away_team': opponent_abbr if is_home else team_abbr,
        'away_team_abbreviation': opponent_abbr if is_home else team_abbr,
        'season': row.get('SEASON', '')
    }
    
    game = create_game(db, game_data)
    
    # Prepare stats data
    stats_data = {
        'player_id': player_id,
        'game_id': game.id,
        'is_home': is_home,
        'opponent_team': opponent_abbr,
        'opponent_abbreviation': opponent_abbr,
        'rest_days': rest_days,
        'minutes': float(row.get('MIN', 0) or 0),
        'points': int(row.get('PTS', 0) or 0),
        'rebounds': int(row.get('REB', 0) or 0),
        'assists': int(row.get('AST', 0) or 0),
        'steals': int(row.get('STL', 0) or 0),
        'blocks': int(row.get('BLK', 0) or 0),
        'turnovers': int(row.get('TOV', 0) or 0),
        'fg_made': int(row.get('FGM', 0) or 0),
        'fg_attempted': int(row.get('FGA', 0) or 0),
        'fg_pct': float(row.get('FG_PCT', 0) or 0),
        'fg3_made': int(row.get('FG3M', 0) or 0),
        'fg3_attempted': int(row.get('FG3A', 0) or 0),
        'fg3_pct': float(row.get('FG3_PCT', 0) or 0),
        'ft_made': int(row.get('FTM', 0) or 0),
        'ft_attempted': int(row.get('FTA', 0) or 0),
        'ft_pct': float(row.get('FT_PCT', 0) or 0),
        'plus_minus': int(row.get('PLUS_MINUS', 0) or 0),
    }
    
    return game, stats_data


def seed_players(db: Session, player_names: List[str], seasons: List[str]) -> int:
    """Seed players and their stats into the database."""
    total_stats = 0
    
    for i, name in enumerate(player_names):
        logger.info(f"[{i+1}/{len(player_names)}] Processing {name}...")
        
        # Get NBA player ID
        nba_id = get_nba_player_id(name)
        if not nba_id:
            logger.warning(f"  Player not found: {name}")
            continue
        
        # Get player info
        info = get_player_info(nba_id)
        if not info:
            logger.warning(f"  Could not get info for {name}")
            continue
        
        # Create/update player
        player = create_player(db, info)
        logger.info(f"  Created player: {player.name} ({player.team_abbreviation})")
        
        # Get game logs
        game_logs = get_player_game_logs(nba_id, seasons)
        if game_logs.empty:
            logger.warning(f"  No game logs found for {name}")
            continue
        
        # Sort by date
        game_logs['GAME_DATE'] = pd.to_datetime(game_logs['GAME_DATE'])
        game_logs = game_logs.sort_values('GAME_DATE')
        
        # Process each game
        prev_game_date = None
        stats_count = 0
        
        for _, row in game_logs.iterrows():
            try:
                game, stats_data = parse_game_log(row, player.id, db, prev_game_date)
                
                # Check if stats already exist
                existing = db.query(PlayerStats).filter(
                    PlayerStats.player_id == player.id,
                    PlayerStats.game_id == game.id
                ).first()
                
                if not existing:
                    create_stats(db, stats_data)
                    stats_count += 1
                
                prev_game_date = pd.to_datetime(row['GAME_DATE']).date()
                
            except Exception as e:
                logger.warning(f"  Error processing game: {e}")
                continue
        
        total_stats += stats_count
        logger.info(f"  Added {stats_count} game stats")
    
    return total_stats


def train_models(db: Session):
    """Train ML models on all player data."""
    logger.info("Preparing training data...")
    
    # Get all player stats
    all_stats = []
    players = db.query(Player).filter(Player.is_active == True).all()
    
    for player in players:
        from app.services import PlayerService
        df = PlayerService.get_player_stats_dataframe(db, player.id)
        if not df.empty:
            df['player_id'] = player.id
            all_stats.append(df)
    
    if not all_stats:
        logger.error("No stats data found for training")
        return
    
    combined_df = pd.concat(all_stats, ignore_index=True)
    logger.info(f"Training on {len(combined_df)} total game records")
    
    # Train models
    metrics = predictor.train(combined_df)
    
    if metrics:
        logger.info("Model training complete!")
        for target, m in metrics.items():
            logger.info(f"  {target}: MAE={m['mae']:.2f}, RMSE={m['rmse']:.2f}, R²={m['r2']:.3f}")
    else:
        logger.error("Model training failed")


def main():
    """Main seed function."""
    logger.info("=" * 60)
    logger.info("NBA Player Performance Prediction - Data Seed Script")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Define seasons to fetch (current and previous)
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # NBA season spans two years (e.g., 2023-24)
        if current_month >= 10:  # Season starts in October
            seasons = [f"{current_year-1}-{str(current_year)[2:]}", f"{current_year}-{str(current_year+1)[2:]}"]
        else:
            seasons = [f"{current_year-2}-{str(current_year-1)[2:]}", f"{current_year-1}-{str(current_year)[2:]}"]
        
        logger.info(f"Fetching data for seasons: {seasons}")
        
        # Seed players
        total_stats = seed_players(db, TOP_PLAYER_NAMES, seasons)
        
        logger.info(f"\nSeeding complete! Added {total_stats} game stat records")
        
        # Train models
        logger.info("\nTraining ML models...")
        train_models(db)
        
        logger.info("\n" + "=" * 60)
        logger.info("Data seeding and model training complete!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
