"""
Collect ALL active NBA players including 2025 rookies.
Then filter by recent activity to exclude long-term injuries/inactive players.
"""

import pandas as pd
import numpy as np
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, commonplayerinfo
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class CompleteDatesetCollector:
    """
    Collect complete NBA dataset with smart filtering.
    
    Features:
    - Collects ALL ~450 active players
    - Includes 2025 rookies automatically
    - Filters by recent activity (last 6 months)
    - Tracks player injury/inactive status
    - Calculates games played rate
    """
    
    def __init__(self, output_dir: str = 'backend/data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Collection settings
        self.seasons = ['2023-24', '2024-25', '2025-26']
        self.rate_limit = 0.6  # Seconds between API calls
        
        # Filtering thresholds
        self.min_games_total = 5  # Minimum 5 games across both seasons
        self.months_inactive_threshold = 6  # Flag if no games in 6 months
        
        # Progress tracking
        self.progress_file = self.output_dir / 'collection_progress.json'
        self.completed_players = self._load_progress()
        
    def _load_progress(self) -> set:
        """Load previous progress"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                return set(progress.get('completed', []))
        return set()
    
    def _save_progress(self, player_id: int):
        """Save progress after each player"""
        self.completed_players.add(player_id)
        
        with open(self.progress_file, 'w') as f:
            json.dump({
                'completed': list(self.completed_players),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def collect_all_players(self):
        """Main collection function"""
        
        logger.info("="*80)
        logger.info("COMPLETE NBA DATASET COLLECTION")
        logger.info("="*80)
        
        # Get ALL active players from API
        logger.info("\nFetching active players from NBA API...")
        all_active = players.get_active_players()
        
        logger.info(f"✓ NBA API reports {len(all_active)} active players")
        logger.info(f"  This includes ALL rookies (2024, 2025, etc.)")
        
        # Check existing data
        existing_file = self.output_dir / 'full_nba_game_logs.csv'
        
        if existing_file.exists():
            try:
                existing_df = pd.read_csv(existing_file)
                # Check if 'player_id' column exists
                if 'player_id' in existing_df.columns:
                    existing_players = set(existing_df['player_id'].unique())
                    logger.info(f"\n✓ Found existing dataset: {len(existing_players)} players")
                else:
                    logger.warning("\n⚠️  Existing dataset missing 'player_id' column. Ignoring.")
                    existing_players = set()
            except Exception as e:
                 logger.warning(f"\n⚠️  Error reading existing dataset: {e}. Ignoring.")
                 existing_players = set()
            
            # Determine who to collect
            all_ids = {p['id'] for p in all_active}
            missing_ids = all_ids - existing_players - self.completed_players
            
            logger.info(f"  Already collected: {len(self.completed_players)}")
            logger.info(f"  Need to collect: {len(missing_ids)}")
            
            if len(missing_ids) == 0:
                logger.info("\n✓ All players already collected!")
                return self._load_and_process_data()
            
            players_to_collect = [p for p in all_active if p['id'] in missing_ids]
            merge_mode = True
        else:
            players_to_collect = all_active
            merge_mode = False
            logger.info(f"\nNo existing data - will collect all {len(all_active)} players")
        
        # Estimate time
        estimated_time = len(players_to_collect) * self.rate_limit * len(self.seasons) / 60
        
        logger.info(f"\n{'='*80}")
        logger.info(f"COLLECTION PLAN")
        logger.info(f"{'='*80}")
        logger.info(f"Players to collect: {len(players_to_collect)}")
        logger.info(f"Seasons: {', '.join(self.seasons)}")
        logger.info(f"Estimated time: {estimated_time:.1f} minutes")
        logger.info(f"Rate limit: {self.rate_limit}s between requests")
        
        # Auto-proceed for non-interactive execution (uncomment input for interactive)
        # response = input("\nProceed with collection? (yes/no): ")
        # if response.lower() != 'yes':
        #     logger.info("Aborted")
        #     return None
        
        # Collect data
        all_game_logs = []
        player_metadata = []
        
        stats = {
            'successful': 0,
            'no_games': 0,
            'failed': 0
        }
        
        logger.info(f"\n{'='*80}")
        logger.info("COLLECTING PLAYER DATA")
        logger.info(f"{'='*80}")
        
        for i, player in enumerate(players_to_collect, 1):
            player_id = player['id']
            player_name = player['full_name']
            
            # Use direct print to avoid double newlines with logger handlers if any
            print(f"[{i}/{len(players_to_collect)}] {player_name}...", end=" ", flush=True)
            
            # Skip if already completed
            if player_id in self.completed_players:
                print("⏭️  (already collected)")
                continue
            
            try:
                # Collect game logs
                player_games = []
                
                for season in self.seasons:
                    time.sleep(self.rate_limit)
                    
                    try:
                        gamelog = playergamelog.PlayerGameLog(
                            player_id=player_id,
                            season=season
                        ).get_data_frames()[0]
                        
                        if len(gamelog) > 0:
                            gamelog['player_id'] = player_id
                            gamelog['player_name'] = player_name
                            gamelog['season'] = season
                            player_games.append(gamelog)
                    except Exception as e:
                         # Log error but continue to next season
                         # logger.debug(f"Error fetching season {season} for {player_name}: {e}")
                         pass

                
                # Process results
                if player_games:
                    combined_games = pd.concat(player_games, ignore_index=True)
                    all_game_logs.append(combined_games)
                    
                    # Track metadata
                    total_games = len(combined_games)
                    last_game_date = pd.to_datetime(combined_games['GAME_DATE']).max()
                    days_since_last_game = (datetime.now() - last_game_date).days
                    
                    player_metadata.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'total_games': total_games,
                        'last_game_date': last_game_date,
                        'days_since_last_game': days_since_last_game
                    })
                    
                    print(f"✓ ({total_games} games, last: {days_since_last_game}d ago)")
                    stats['successful'] += 1
                else:
                    print(f"⚪ (0 games - never played or inactive)")
                    
                    player_metadata.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'total_games': 0,
                        'last_game_date': None,
                        'days_since_last_game': 999
                    })
                    
                    stats['no_games'] += 1
                
                # Save progress
                self._save_progress(player_id)
                
                # Checkpoint every 25 players
                if i % 25 == 0:
                    logger.info(f"\n  💾 Checkpoint: {stats['successful']} successful, {stats['no_games']} no games, {stats['failed']} failed")
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
                stats['failed'] += 1
        
        logger.info(f"\n{'='*80}")
        logger.info("COLLECTION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Successful: {stats['successful']}")
        logger.info(f"No games: {stats['no_games']}")
        logger.info(f"Failed: {stats['failed']}")
        
        if not all_game_logs:
            logger.info("\n⚠️  No new game data collected or all already collected.")
             # If merging with existing data and we found no NEW data, we might still want to return existing metadata
             # But _process_and_save_data handles merging, so we can pass empty list if merge_mode is True
            if not merge_mode:
                 return None
        
        # Process collected data
        return self._process_and_save_data(all_game_logs, player_metadata, merge_mode)
    
    def _process_and_save_data(
        self, 
        game_logs: list, 
        metadata: list,
        merge_mode: bool
    ) -> pd.DataFrame:
        """Process and save collected data"""
        
        logger.info(f"\n{'='*80}")
        logger.info("PROCESSING DATA")
        logger.info(f"{'='*80}")
        
        df_new = pd.DataFrame()

        if game_logs:
            # Combine game logs
            df_new = pd.concat(game_logs, ignore_index=True)
            logger.info(f"✓ Combined {len(df_new):,} new games from {df_new['player_name'].nunique()} players")
            
            # Standardize column names
            column_mapping = {
                'GAME_DATE': 'game_date',
                'MATCHUP': 'matchup',
                'WL': 'win_loss',
                'MIN': 'minutes',
                'PTS': 'points',
                'REB': 'rebounds',
                'AST': 'assists',
                'STL': 'steals',
                'BLK': 'blocks',
                'TOV': 'turnovers',
                'FGA': 'field_goal_attempts',
                'FGM': 'field_goals_made',
                'FG_PCT': 'field_goal_pct',
                'FG3A': 'three_point_attempts',
                'FG3M': 'three_pointers_made',
                'FG3_PCT': 'three_point_pct',
                'FTA': 'free_throw_attempts',
                'FTM': 'free_throws_made',
                'FT_PCT': 'free_throw_pct',
                'PLUS_MINUS': 'plus_minus',
            }
            
            df_new = df_new.rename(columns=column_mapping)
            
            # Process dates
            df_new['game_date'] = pd.to_datetime(df_new['game_date'])
            
            # Parse minutes (handle "MM:SS" format)
            def parse_minutes(min_str):
                try:
                    if pd.isna(min_str) or min_str == 0:
                        return 0.0
                    if isinstance(min_str, (int, float)):
                        return float(min_str)
                    if ':' in str(min_str):
                        parts = str(min_str).split(':')
                        minutes = int(parts[0])
                        seconds = int(parts[1]) if len(parts) > 1 else 0
                        return minutes + seconds / 60.0
                    return float(min_str)
                except:
                    return 0.0
            
            if 'minutes' in df_new.columns:
                if df_new['minutes'].dtype == 'object':
                    df_new['minutes'] = df_new['minutes'].apply(parse_minutes)
            
                # Extract home/away and opponent
                if 'matchup' in df_new.columns:
                    df_new['home_game'] = df_new['matchup'].str.contains('vs.').fillna(False).astype(int)
                    df_new['opponent'] = df_new['matchup'].str.extract(r'(?:vs\.|@)\s*([A-Z]+)')
                
                # Remove games with 0 minutes (DNP - Did Not Play)
                initial_len = len(df_new)
                df_new = df_new[df_new['minutes'] > 0].copy()
                logger.info(f"✓ Removed {initial_len - len(df_new):,} DNP games (0 minutes)")
        
        # Merge with existing data if needed
        if merge_mode:
            existing_file = self.output_dir / 'full_nba_game_logs.csv'
            if existing_file.exists():
                try:
                    df_existing = pd.read_csv(existing_file)
                    df_existing['game_date'] = pd.to_datetime(df_existing['game_date'])
                    
                    logger.info(f"\n✓ Merging with existing data ({len(df_existing):,} games)")
                    
                    if not df_new.empty:
                        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    else:
                        df_combined = df_existing

                    df_combined = df_combined.drop_duplicates(
                        subset=['player_id', 'game_date'], 
                        keep='last'
                    )
                    
                    logger.info(f"✓ After deduplication: {len(df_combined):,} games")
                except Exception as e:
                    logger.error(f"Error merging existing data: {e}")
                    df_combined = df_new
            else:
                df_combined = df_new
        else:
            df_combined = df_new
        
        if df_combined.empty:
            logger.warning("No data to save.")
            return df_combined

        # Sort by player and date
        if 'player_id' in df_combined.columns and 'game_date' in df_combined.columns:
            df_combined = df_combined.sort_values(['player_id', 'game_date']).reset_index(drop=True)
        
        # Save main dataset
        output_file = self.output_dir / 'full_nba_game_logs.csv'
        df_combined.to_csv(output_file, index=False)
        
        logger.info(f"\n✓ Saved dataset to {output_file}")
        
        # Save metadata
        df_metadata = pd.DataFrame(metadata)
        metadata_file = self.output_dir / 'player_metadata.csv'
        # If metadata file exists, append/update?
        # For simplicity in this script as designed, we might overwrite if running fresh
        # or we might want to load existing metadata.
        # Given the prompt implies run once to get COMPLETE dataset, we'll just rewrite it
        # or ideally merge it if we want to be safe.
        
        if metadata_file.exists():
             try:
                existing_metadata = pd.read_csv(metadata_file)
                if not df_metadata.empty:
                    # Merge logic: update existing rows, add new ones
                    # Using player_id as key
                    combined_metadata = pd.concat([existing_metadata, df_metadata])
                    combined_metadata = combined_metadata.drop_duplicates(subset=['player_id'], keep='last')
                    df_metadata = combined_metadata
                else:
                    df_metadata = existing_metadata
             except:
                 pass

        if not df_metadata.empty:
            df_metadata.to_csv(metadata_file, index=False)
            logger.info(f"✓ Saved metadata to {metadata_file}")
        
        return df_combined
    
    def _load_and_process_data(self) -> pd.DataFrame:
        """Load existing data and add metadata"""
        existing_file = self.output_dir / 'full_nba_game_logs.csv'
        df = pd.read_csv(existing_file)
        df['game_date'] = pd.to_datetime(df['game_date'])
        return df


def analyze_player_activity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze player activity and flag inactive/injured players.
    
    Returns:
        DataFrame with activity metrics for each player
    """
    
    logger.info(f"\n{'='*80}")
    logger.info("ANALYZING PLAYER ACTIVITY")
    logger.info(f"{'='*80}")
    
    if df.empty:
        logger.warning("Empty dataframe, cannot analyze activity.")
        return pd.DataFrame()

    # Calculate per-player metrics
    # Ensure required columns exist
    required_cols = ['player_id', 'player_name', 'game_date', 'minutes', 'points']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
         logger.error(f"Missing columns for analysis: {missing_cols}")
         return pd.DataFrame()

    player_stats = df.groupby(['player_id', 'player_name']).agg({
        'game_date': ['min', 'max', 'count'],
        'minutes': 'mean',
        'points': 'mean'
    }).reset_index()
    
    player_stats.columns = [
        'player_id', 'player_name',
        'first_game', 'last_game', 'total_games',
        'avg_minutes', 'avg_points'
    ]
    
    # Calculate days since last game
    today = datetime.now()
    player_stats['days_since_last_game'] = (
        today - pd.to_datetime(player_stats['last_game'])
    ).dt.days
    
    # Calculate games in last 6 months
    six_months_ago = today - timedelta(days=180)
    
    recent_games = df[df['game_date'] >= six_months_ago].groupby('player_name').size()
    player_stats['games_last_6_months'] = player_stats['player_name'].map(recent_games).fillna(0).astype(int)
    
    # Flag inactive players
    player_stats['is_active'] = (
        (player_stats['days_since_last_game'] < 180) &  # Played in last 6 months
        (player_stats['total_games'] >= 5) &            # At least 5 games total
        (player_stats['avg_minutes'] >= 5)              # Average 5+ minutes
    )
    
    # Categorize players
    def categorize_player(row):
        if row['days_since_last_game'] > 180:
            return 'INACTIVE_6M+'
        elif row['total_games'] < 5:
            return 'INSUFFICIENT_GAMES'
        elif row['avg_minutes'] < 5:
            return 'MINIMAL_MINUTES'
        elif row['games_last_6_months'] < 3:
            return 'RARELY_PLAYS'
        else:
            return 'ACTIVE'
    
    player_stats['activity_status'] = player_stats.apply(categorize_player, axis=1)
    
    # Print summary
    logger.info(f"\nTotal players: {len(player_stats)}")
    logger.info(f"\nActivity breakdown:")
    logger.info(player_stats['activity_status'].value_counts())
    
    logger.info(f"\nActive players (fantasy-relevant): {player_stats['is_active'].sum()}")
    logger.info(f"Inactive players (exclude from rankings): {(~player_stats['is_active']).sum()}")
    
    # Show examples of inactive players
    inactive = player_stats[~player_stats['is_active']].sort_values('days_since_last_game', ascending=False)
    
    if len(inactive) > 0:
        logger.info(f"\nExamples of inactive players (will exclude from fantasy rankings):")
        # Convert to string and log line by line or as a block
        logger.info(inactive[['player_name', 'total_games', 'days_since_last_game', 'activity_status']].head(10).to_string(index=False))
    
    return player_stats


def generate_activity_report(df: pd.DataFrame, player_stats: pd.DataFrame, output_dir: Path):
    """Generate comprehensive activity report"""
    
    report = []
    report.append("="*80)
    report.append("NBA PLAYER ACTIVITY REPORT")
    report.append("="*80)
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall stats
    report.append(f"\n{'='*80}")
    report.append("DATASET SUMMARY")
    report.append(f"{'='*80}")
    report.append(f"Total players: {len(player_stats)}")
    report.append(f"Total games: {len(df):,}")
    report.append(f"Date range: {df['game_date'].min()} to {df['game_date'].max()}")
    
    # Activity breakdown
    report.append(f"\n{'='*80}")
    report.append("PLAYER ACTIVITY STATUS")
    report.append(f"{'='*80}")
    
    status_counts = player_stats['activity_status'].value_counts()
    for status, count in status_counts.items():
        pct = count / len(player_stats) * 100
        report.append(f"{status:20} {count:4} ({pct:5.1f}%)")
    
    # Active players for fantasy
    report.append(f"\n{'='*80}")
    report.append("FANTASY BASKETBALL ELIGIBILITY")
    report.append(f"{'='*80}")
    
    active_count = player_stats['is_active'].sum()
    inactive_count = (~player_stats['is_active']).sum()
    
    report.append(f"Fantasy-eligible (active): {active_count}")
    report.append(f"Exclude from rankings: {inactive_count}")
    
    # Players to exclude
    report.append(f"\n{'='*80}")
    report.append("PLAYERS TO EXCLUDE FROM FANTASY RANKINGS")
    report.append(f"{'='*80}")
    report.append(f"(Players who haven't played in 6+ months or have insufficient data)")
    report.append("")
    
    inactive = player_stats[~player_stats['is_active']].sort_values('days_since_last_game', ascending=False)
    
    for _, player in inactive.head(50).iterrows():
        report.append(
            f"{player['player_name']:30} "
            f"Games: {player['total_games']:3} | "
            f"Last game: {player['days_since_last_game']:4}d ago | "
            f"Status: {player['activity_status']}"
        )
    
    # Verification checks
    report.append(f"\n{'='*80}")
    report.append("VERIFICATION: KEY PLAYERS")
    report.append(f"{'='*80}")
    
    test_players = [
        'Ace Bailey', 'LeBron James', 'Victor Wembanyama', 
        'John Collins', 'Jayson Tatum', 'Stephen Curry'
    ]
    
    for name in test_players:
        player_row = player_stats[player_stats['player_name'] == name]
        
        if len(player_row) > 0:
            p = player_row.iloc[0]
            report.append(
                f"✓ {name:25} Games: {p['total_games']:3} | "
                f"Status: {p['activity_status']:20} | "
                f"Active: {'YES' if p['is_active'] else 'NO'}"
            )
        else:
            report.append(f"✗ {name:25} NOT FOUND IN DATASET")
    
    report.append("\n" + "="*80)
    
    # Save report
    output_dir.mkdir(exist_ok=True, parents=True)
    report_file = output_dir / 'player_activity_report.txt'
    with open(report_file, 'w') as f:
        f.write('\n'.join(report))
    
    logger.info(f"\n✓ Activity report saved to {report_file}")


def main():
    """Main execution function"""
    
    logger.info("="*80)
    logger.info(" "*20 + "COMPLETE NBA DATASET COLLECTION")
    logger.info("="*80)
    logger.info("\nThis script will:")
    logger.info("  1. Collect ALL ~450 active NBA players (including 2025 rookies)")
    logger.info("  2. Identify inactive players (no games in 6+ months)")
    logger.info("  3. Flag players to exclude from fantasy rankings")
    logger.info("="*80)
    
    # Initialize collector
    collector = CompleteDatesetCollector(output_dir='backend/data')
    
    # Collect all players
    df = collector.collect_all_players()
    
    if df is None:
        logger.info("\n⚠️  No data to process")
        return
    
    # Analyze player activity
    player_stats = analyze_player_activity(df)
    
    if not player_stats.empty:
        # Generate report
        generate_activity_report(df, player_stats, Path('./reports'))
        
        # Save player stats
        player_stats.to_csv('data/player_activity_stats.csv', index=False)
        logger.info(f"\n✓ Player activity stats saved to data/player_activity_stats.csv")
        
        # Final summary
        logger.info(f"\n{'='*80}")
        logger.info("COLLECTION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total players in dataset: {len(player_stats)}")
        logger.info(f"Fantasy-eligible players: {player_stats['is_active'].sum()}")
        logger.info(f"Excluded (inactive 6m+): {(~player_stats['is_active']).sum()}")
        
        logger.info(f"\nNext steps:")
        logger.info(f"  1. Review: reports/player_activity_report.txt")
        logger.info(f"  2. Update draft_helper.py to filter inactive players")
        logger.info(f"  3. Retrain models on complete dataset")
    else:
        logger.error("Failed to generate player stats.")


if __name__ == "__main__":
    main()
