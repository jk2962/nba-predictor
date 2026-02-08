"""
NBA Dataset Expansion Script
Downloads game logs for 200+ active players across 2 seasons.
Includes rate limiting, error handling, resume capability, and progress tracking.

Usage:
    python -m scripts.collect_full_nba_dataset

Target: 200+ players, 15,000+ games, 2 seasons
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import pickle
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

try:
    from nba_api.stats.endpoints import playergamelog, leaguedashplayerstats
    from nba_api.stats.static import players
    HAS_NBA_API = True
except ImportError:
    HAS_NBA_API = False
    logger.error("nba_api not installed! Run: pip install nba_api")


class NBADataCollector:
    """
    Comprehensive NBA data collector with stratified sampling and resume capability.
    Target: 200+ players, 15,000+ games, 2 seasons
    """
    
    def __init__(self, output_dir: str = './data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / 'collection_progress.json'
        self.checkpoint_file = self.output_dir / 'collection_checkpoint.pkl'
        
        # Data storage
        self.all_game_logs: List[pd.DataFrame] = []
        self.player_info: Dict = {}
        self.failed_players: List[Dict] = []
        
        # Collection settings
        self.seasons = ['2023-24', '2024-25']
        self.rate_limit_delay = 0.7  # Seconds between API calls
        
        # Load progress if exists
        self.completed_players = self._load_progress()
    
    def _load_progress(self) -> set:
        """Load previously completed players to resume collection"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                completed = set(progress.get('completed', []))
                if completed:
                    logger.info(f"📂 Resuming: {len(completed)} players already collected")
                return completed
        return set()
    
    def _save_progress(self, player_id: int):
        """Save progress after each player"""
        self.completed_players.add(player_id)
        
        with open(self.progress_file, 'w') as f:
            json.dump({
                'completed': list(self.completed_players),
                'failed': self.failed_players,
                'last_updated': datetime.now().isoformat(),
                'total_games': sum(len(df) for df in self.all_game_logs)
            }, f, indent=2)
    
    def _save_checkpoint(self):
        """Save full checkpoint of collected data"""
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump({
                'game_logs': self.all_game_logs,
                'player_info': self.player_info,
                'failed_players': self.failed_players
            }, f)
    
    def _load_checkpoint(self) -> bool:
        """Load checkpoint if exists"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    data = pickle.load(f)
                    self.all_game_logs = data.get('game_logs', [])
                    self.player_info = data.get('player_info', {})
                    self.failed_players = data.get('failed_players', [])
                    logger.info(f"📂 Loaded checkpoint: {len(self.all_game_logs)} player datasets")
                    return True
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return False
    
    def get_target_players(self, min_players: int = 200) -> List[Dict]:
        """
        Get stratified sample of NBA players across positions and skill levels.
        """
        logger.info("\n" + "="*70)
        logger.info("IDENTIFYING TARGET PLAYERS")
        logger.info("="*70)
        
        # Get all active players
        all_active = players.get_active_players()
        logger.info(f"\nTotal active NBA players: {len(all_active)}")
        
        # Get current season stats
        logger.info("Fetching 2024-25 season stats...")
        time.sleep(self.rate_limit_delay)
        
        try:
            season_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season='2024-25',
                per_mode_detailed='PerGame'
            ).get_data_frames()[0]
            
            logger.info(f"Found {len(season_stats)} players with 2024-25 stats")
            
        except Exception as e:
            logger.warning(f"Could not fetch 2024-25 stats: {e}")
            logger.info("Trying 2023-24 season...")
            
            try:
                time.sleep(self.rate_limit_delay)
                season_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                    season='2023-24',
                    per_mode_detailed='PerGame'
                ).get_data_frames()[0]
            except Exception as e2:
                logger.error(f"Failed to fetch season stats: {e2}")
                # Fallback to all active players
                return all_active[:min_players]
        
        # Filter to players with meaningful stats (at least 5 games)
        if 'GP' in season_stats.columns:
            season_stats = season_stats[season_stats['GP'] >= 5]
        
        # Create PPG tiers
        season_stats['ppg_tier'] = pd.cut(
            season_stats['PTS'],
            bins=[-1, 5, 12, 20, 100],
            labels=['bench', 'role', 'starter', 'star']
        )
        
        # Get player positions from the stats
        # Note: nba_api doesn't always have positions, so we'll use a simplified approach
        target_players = []
        
        # Sort by points to get a good mix
        season_stats = season_stats.sort_values('PTS', ascending=False)
        
        # Select players by tier
        tier_targets = {
            'star': 50,      # >20 PPG
            'starter': 60,   # 12-20 PPG  
            'role': 60,      # 5-12 PPG
            'bench': 40      # <5 PPG
        }
        
        for tier, target_count in tier_targets.items():
            tier_players = season_stats[season_stats['ppg_tier'] == tier].head(target_count)
            
            for _, row in tier_players.iterrows():
                # Find in all_active
                player_match = [
                    p for p in all_active 
                    if p['full_name'] == row['PLAYER_NAME']
                ]
                
                if player_match:
                    player = player_match[0].copy()
                    player['ppg_tier'] = tier
                    player['ppg'] = row['PTS']
                    player['gp'] = row.get('GP', 0)
                    target_players.append(player)
        
        logger.info(f"\n✓ Selected {len(target_players)} players")
        
        # Print distribution
        tier_dist = {}
        for p in target_players:
            tier = p.get('ppg_tier', 'unknown')
            tier_dist[tier] = tier_dist.get(tier, 0) + 1
        
        logger.info("\nPlayer distribution by tier:")
        for tier, count in sorted(tier_dist.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {tier:15} {count:3} players")
        
        return target_players
    
    def collect_player_game_logs(
        self, 
        player: Dict,
        seasons: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, bool]:
        """Collect game logs for a single player across multiple seasons."""
        if seasons is None:
            seasons = self.seasons
        
        player_id = player['id']
        player_name = player['full_name']
        
        # Check if already completed
        if player_id in self.completed_players:
            return pd.DataFrame(), True  # Already done
        
        all_seasons_data = []
        
        for season in seasons:
            try:
                time.sleep(self.rate_limit_delay)
                
                gamelog = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season
                ).get_data_frames()[0]
                
                if len(gamelog) > 0:
                    gamelog['player_id'] = player_id
                    gamelog['player_name'] = player_name
                    gamelog['season'] = season
                    gamelog['ppg_tier'] = player.get('ppg_tier', 'unknown')
                    
                    all_seasons_data.append(gamelog)
                    
            except Exception as e:
                # Don't log every failure, just continue
                continue
        
        if all_seasons_data:
            combined = pd.concat(all_seasons_data, ignore_index=True)
            return combined, True
        else:
            return pd.DataFrame(), False
    
    def collect_all_data(self, target_players: List[Dict]):
        """Main collection loop with progress tracking."""
        logger.info("\n" + "="*70)
        logger.info("COLLECTING GAME LOGS")
        logger.info("="*70)
        
        # Load checkpoint if exists
        self._load_checkpoint()
        
        total = len(target_players)
        remaining = total - len(self.completed_players)
        
        logger.info(f"\nTarget: {total} players")
        logger.info(f"Already completed: {len(self.completed_players)}")
        logger.info(f"Remaining: {remaining}")
        logger.info(f"Rate limit: {self.rate_limit_delay}s between requests")
        
        est_time = remaining * self.rate_limit_delay * len(self.seasons) / 60
        logger.info(f"Estimated time: {est_time:.1f} minutes")
        
        start_time = time.time()
        successful = 0
        failed = 0
        
        for i, player in enumerate(target_players, 1):
            player_name = player['full_name']
            player_id = player['id']
            
            # Skip if already done
            if player_id in self.completed_players:
                continue
            
            # Collect
            game_logs, success = self.collect_player_game_logs(player)
            
            if success and len(game_logs) > 0:
                self.all_game_logs.append(game_logs)
                successful += 1
                self._save_progress(player_id)
                
                # Progress indicator
                if successful % 10 == 0:
                    total_games = sum(len(df) for df in self.all_game_logs)
                    elapsed = time.time() - start_time
                    logger.info(f"  [{successful}/{remaining}] {total_games:,} games collected... ({elapsed/60:.1f}m)")
                
                # Checkpoint every 25 players
                if successful % 25 == 0:
                    self._save_checkpoint()
                    logger.info(f"  💾 Checkpoint saved")
            else:
                failed += 1
                self.failed_players.append({
                    'id': player_id,
                    'name': player_name
                })
        
        # Final save
        self._save_checkpoint()
        
        total_games = sum(len(df) for df in self.all_game_logs)
        elapsed = time.time() - start_time
        
        logger.info("\n" + "="*70)
        logger.info("COLLECTION COMPLETE")
        logger.info("="*70)
        logger.info(f"Players collected: {len(self.all_game_logs)}")
        logger.info(f"Total games: {total_games:,}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Time: {elapsed/60:.1f} minutes")
    
    def combine_and_clean_data(self) -> pd.DataFrame:
        """Combine all game logs and clean data."""
        logger.info("\n" + "="*70)
        logger.info("COMBINING AND CLEANING DATA")
        logger.info("="*70)
        
        if not self.all_game_logs:
            # Try loading checkpoint
            self._load_checkpoint()
            
        if not self.all_game_logs:
            logger.error("No game logs collected!")
            return pd.DataFrame()
        
        df = pd.concat(self.all_game_logs, ignore_index=True)
        logger.info(f"Raw games: {len(df):,}")
        
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
            'FG_PCT': 'fg_pct',
            'FG3A': 'three_point_attempts',
            'FG3M': 'three_pointers_made',
            'FG3_PCT': 'fg3_pct',
            'FTA': 'free_throw_attempts',
            'FTM': 'free_throws_made',
            'FT_PCT': 'ft_pct',
            'PLUS_MINUS': 'plus_minus',
        }
        
        df = df.rename(columns=column_mapping)
        
        # Parse dates
        df['game_date'] = pd.to_datetime(df['game_date'])
        
        # Extract home/away
        if 'matchup' in df.columns:
            df['is_home'] = df['matchup'].str.contains('vs.').astype(int)
            df['opponent'] = df['matchup'].str.extract(r'(?:vs\.|@)\s*([A-Z]+)')
        
        # Parse minutes
        if df['minutes'].dtype == 'object':
            df['minutes'] = df['minutes'].apply(self._parse_minutes)
        
        # Remove DNP games
        initial = len(df)
        df = df[df['minutes'] > 0].copy()
        logger.info(f"Removed {initial - len(df)} DNP games")
        
        # Remove missing core stats
        required = ['points', 'rebounds', 'assists']
        df = df.dropna(subset=required)
        
        # Fill missing percentages
        for col in ['fg_pct', 'fg3_pct', 'ft_pct']:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # Add rest days
        df = df.sort_values(['player_id', 'game_date'])
        df['rest_days'] = df.groupby('player_id')['game_date'].diff().dt.days.fillna(3)
        df['rest_days'] = df['rest_days'].clip(0, 7)
        
        df = df.reset_index(drop=True)
        
        logger.info(f"✓ Final dataset: {len(df):,} games, {df['player_id'].nunique()} players")
        
        return df
    
    def _parse_minutes(self, min_str) -> float:
        """Convert minutes string to float."""
        try:
            if pd.isna(min_str) or min_str == '0' or min_str == 0:
                return 0.0
            if isinstance(min_str, (int, float)):
                return float(min_str)
            if ':' in str(min_str):
                parts = str(min_str).split(':')
                return int(parts[0]) + int(parts[1]) / 60.0
            return float(min_str)
        except:
            return 0.0
    
    def generate_report(self, df: pd.DataFrame) -> bool:
        """Generate quality report and check success criteria."""
        logger.info("\n" + "="*70)
        logger.info("DATA QUALITY REPORT")
        logger.info("="*70)
        
        # Basic stats
        n_players = df['player_id'].nunique()
        n_games = len(df)
        
        logger.info(f"\n📊 DATASET OVERVIEW")
        logger.info(f"  Total games:      {n_games:,}")
        logger.info(f"  Unique players:   {n_players}")
        logger.info(f"  Date range:       {df['game_date'].min().date()} to {df['game_date'].max().date()}")
        
        # Games per player
        gpp = df.groupby('player_id').size()
        logger.info(f"\n📈 GAMES PER PLAYER")
        logger.info(f"  Mean:   {gpp.mean():.1f}")
        logger.info(f"  Median: {gpp.median():.1f}")
        logger.info(f"  Range:  {gpp.min()} - {gpp.max()}")
        
        # Tier distribution
        if 'ppg_tier' in df.columns:
            logger.info(f"\n⭐ PLAYERS BY TIER")
            tier_counts = df.groupby('ppg_tier')['player_id'].nunique()
            for tier, count in tier_counts.items():
                logger.info(f"  {tier:15} {count:3} players")
        
        # Stats summary
        logger.info(f"\n📈 STATS RANGES")
        for stat in ['points', 'rebounds', 'assists']:
            logger.info(f"  {stat.capitalize():10} mean={df[stat].mean():.1f}, max={df[stat].max():.0f}")
        
        # Success criteria
        logger.info(f"\n🎯 SUCCESS CRITERIA")
        
        criteria = {
            'Players ≥ 200': n_players >= 200,
            'Games ≥ 15,000': n_games >= 15000,
            'Avg games/player ≥ 50': gpp.mean() >= 50,
        }
        
        all_pass = True
        for crit, passed in criteria.items():
            status = "✓" if passed else "✗"
            logger.info(f"  {status} {crit}")
            if not passed:
                all_pass = False
        
        return all_pass
    
    def save_to_database(self, df: pd.DataFrame, db_path: str = 'data/nba.db'):
        """Save expanded dataset to SQLite database."""
        logger.info(f"\n💾 Saving to database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        
        # Create players table
        players_df = df.groupby('player_id').agg({
            'player_name': 'first',
            'ppg_tier': 'first'
        }).reset_index()
        players_df.columns = ['id', 'name', 'tier']
        players_df['position'] = 'G'  # Default, ideally fetch actual positions
        players_df['team'] = 'NBA'
        
        # Save players
        players_df.to_sql('players_expanded', conn, if_exists='replace', index=False)
        
        # Save game logs
        df.to_sql('game_logs_expanded', conn, if_exists='replace', index=False)
        
        conn.close()
        logger.info(f"✓ Saved {len(players_df)} players and {len(df):,} games")
    
    def save_csv(self, df: pd.DataFrame, filename: str = 'full_nba_game_logs.csv'):
        """Save final dataset to CSV."""
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        size_mb = filepath.stat().st_size / 1024 / 1024
        logger.info(f"✓ Saved CSV: {filepath} ({size_mb:.1f} MB)")
        return filepath


def main():
    """Main execution."""
    if not HAS_NBA_API:
        logger.error("Cannot run without nba_api!")
        logger.error("Install with: pip install nba_api")
        return
    
    logger.info("="*70)
    logger.info("      NBA DATASET EXPANSION: 50 → 200+ PLAYERS")
    logger.info("="*70)
    logger.info("\nThis will collect 2 seasons of data for 200+ NBA players.")
    logger.info("Estimated time: 30-60 minutes")
    logger.info("="*70)
    
    # Initialize
    collector = NBADataCollector(output_dir='./data')
    
    # Get players
    target_players = collector.get_target_players(min_players=210)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Ready to collect data for {len(target_players)} players")
    logger.info(f"{'='*70}")
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response != 'yes':
        logger.info("Aborted.")
        return
    
    # Collect
    collector.collect_all_data(target_players)
    
    # Clean
    df = collector.combine_and_clean_data()
    
    if len(df) == 0:
        logger.error("No data collected!")
        return
    
    # Report
    success = collector.generate_report(df)
    
    # Save
    collector.save_csv(df)
    collector.save_to_database(df)
    
    logger.info("\n" + "="*70)
    logger.info("COMPLETE!")
    logger.info("="*70)
    
    if success:
        logger.info("✓ All criteria met!")
        logger.info("\nNext steps:")
        logger.info("  1. python -m scripts.retrain_with_expanded_data")
        logger.info("  2. Verify predictions are realistic")
    else:
        logger.info("⚠️ Some criteria not met - consider collecting more data")


if __name__ == "__main__":
    main()
