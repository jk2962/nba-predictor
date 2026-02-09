#!/usr/bin/env python3
"""
Clean up fake 2025 rookie entries from database and CSV files.

These rookies were added with placeholder IDs (2025001-2025005) which don't 
correspond to real NBA API player IDs. This causes data integrity issues.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.cleanup_fake_rookies
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models import Player, PlayerStats

# IDs from inject_2025_rookies.py that are fake
FAKE_ROOKIE_IDS = [2025001, 2025002, 2025003, 2025004, 2025005]
FAKE_ROOKIE_NAMES = ['Ace Bailey', 'Cooper Flagg', 'Dylan Harper', 'V.J. Edgecombe', 'Tre Johnson']


def cleanup_database():
    """Remove fake rookies from the database."""
    print("\n=== Cleaning up database ===")
    
    db = SessionLocal()
    try:
        # Find and delete fake players by their fake IDs
        deleted_count = 0
        for fake_id in FAKE_ROOKIE_IDS:
            player = db.query(Player).filter(Player.nba_id == fake_id).first()
            if player:
                # Delete associated stats first
                stats_deleted = db.query(PlayerStats).filter(PlayerStats.player_id == player.id).delete()
                print(f"  Deleted {stats_deleted} stats records for {player.name}")
                
                # Delete the player
                db.delete(player)
                deleted_count += 1
                print(f"  Deleted player: {player.name} (fake ID: {fake_id})")
        
        db.commit()
        print(f"\nRemoved {deleted_count} fake rookies from database.")
        
    except Exception as e:
        db.rollback()
        print(f"Error cleaning database: {e}")
    finally:
        db.close()


def cleanup_csv_files():
    """Remove fake rookies from CSV data files."""
    print("\n=== Cleaning up CSV files ===")
    
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Files to clean
    csv_files = [
        ('player_activity_stats.csv', 'player_id'),
        ('full_nba_game_logs.csv', 'player_id'),
        ('nba_players_2025-26.csv', 'player_id'),
    ]
    
    for filename, id_column in csv_files:
        filepath = data_dir / filename
        if filepath.exists():
            try:
                df = pd.read_csv(filepath)
                original_len = len(df)
                
                # Remove rows with fake IDs
                df = df[~df[id_column].isin(FAKE_ROOKIE_IDS)]
                
                # Also remove by name if ID column doesn't match
                if 'player_name' in df.columns:
                    df = df[~df['player_name'].isin(FAKE_ROOKIE_NAMES)]
                elif 'name' in df.columns:
                    df = df[~df['name'].isin(FAKE_ROOKIE_NAMES)]
                
                removed = original_len - len(df)
                if removed > 0:
                    df.to_csv(filepath, index=False)
                    print(f"  {filename}: Removed {removed} fake rookie entries")
                else:
                    print(f"  {filename}: No fake rookies found")
                    
            except Exception as e:
                print(f"  Error processing {filename}: {e}")
        else:
            print(f"  {filename}: File not found, skipping")


def show_current_state():
    """Show current state of rookie data."""
    print("\n=== Current Database State ===")
    
    db = SessionLocal()
    try:
        for fake_id in FAKE_ROOKIE_IDS:
            player = db.query(Player).filter(Player.nba_id == fake_id).first()
            if player:
                stats_count = db.query(PlayerStats).filter(PlayerStats.player_id == player.id).count()
                print(f"  FOUND: {player.name} (fake ID: {fake_id}, stats: {stats_count})")
            else:
                print(f"  NOT FOUND: Player with fake ID {fake_id}")
    finally:
        db.close()
        
    print("\n=== Current CSV State ===")
    data_dir = Path(__file__).parent.parent / 'data'
    activity_file = data_dir / 'player_activity_stats.csv'
    
    if activity_file.exists():
        df = pd.read_csv(activity_file)
        fake_rows = df[df['player_id'].isin(FAKE_ROOKIE_IDS)]
        if len(fake_rows) > 0:
            print(f"  Found {len(fake_rows)} fake rookies in activity stats:")
            for _, row in fake_rows.iterrows():
                print(f"    - {row['player_name']} (ID: {row['player_id']})")
        else:
            print("  No fake rookies in activity stats")


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("Fake 2025 Rookie Cleanup Script")
    print("=" * 60)
    print("\nThis script removes placeholder rookie entries that were")
    print("created with fake IDs (2025001-2025005) instead of real NBA API IDs.")
    print("\nRookies to remove:")
    for fake_id, name in zip(FAKE_ROOKIE_IDS, FAKE_ROOKIE_NAMES):
        print(f"  - {name} (fake ID: {fake_id})")
    
    # Show current state
    show_current_state()
    
    # Prompt for confirmation
    print("\n" + "=" * 60)
    response = input("Proceed with cleanup? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Cleanup cancelled.")
        return
    
    # Perform cleanup
    cleanup_csv_files()
    cleanup_database()
    
    print("\n" + "=" * 60)
    print("Cleanup complete!")
    print("\nNote: If you need these players with REAL NBA API IDs,")
    print("run the data sync script: python -m scripts.sync_complete_player_data")


if __name__ == "__main__":
    main()
