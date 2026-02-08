"""
Fix game dates to prevent timezone shifting.
Convert all dates to date-only format (no time component).
"""

import pandas as pd
from datetime import datetime

def fix_game_dates():
    """
    Fix date storage to prevent timezone issues.
    
    Problem: Dates stored as datetime with midnight UTC get shifted
             when displayed in local timezones.
    
    Solution: Store as date strings in 'YYYY-MM-DD' format.
    """
    
    print("="*80)
    print("FIXING GAME DATE TIMEZONE ISSUES")
    print("="*80)
    
    # Load dataset
    df = pd.read_csv('data/full_nba_game_logs.csv')
    
    print(f"\nOriginal dataset:")
    print(f"  Total games: {len(df):,}")
    
    # Check current date format
    print(f"\nCurrent date samples:")
    print(df['game_date'].head(10))
    print(f"\nDate dtype: {df['game_date'].dtype}")
    
    # Convert to datetime (if not already)
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    print(f"\nAfter pd.to_datetime:")
    print(df['game_date'].head(10))
    
    # Extract just the date (no time component)
    # This creates a date string in YYYY-MM-DD format
    df['game_date'] = df['game_date'].dt.date
    
    print(f"\nAfter extracting date only:")
    print(df['game_date'].head(10))
    print(f"\nDate dtype: {type(df['game_date'].iloc[0])}")
    
    # Convert to string format for consistent storage
    df['game_date'] = df['game_date'].astype(str)
    
    print(f"\nFinal format (as strings):")
    print(df['game_date'].head(10))
    print(f"Date dtype: {df['game_date'].dtype}")
    
    # Verify a specific game
    print(f"\n{'='*80}")
    print("VERIFICATION")
    print(f"{'='*80}")
    
    sample_game = df.iloc[0]
    print(f"\nSample game:")
    print(f"  Player: {sample_game['player_name']}")
    print(f"  Date stored: {sample_game['game_date']}")
    print(f"  Matchup: {sample_game.get('matchup', 'N/A')}")
    
    # Save fixed dataset
    df.to_csv('data/full_nba_game_logs.csv', index=False)
    
    print(f"\n✓ Fixed dataset saved to data/full_nba_game_logs.csv")
    print(f"  All dates now in 'YYYY-MM-DD' string format")
    print(f"  No time component = no timezone shifting")
    
    # Test date parsing
    print(f"\n{'='*80}")
    print("TESTING DATE DISPLAY")
    print(f"{'='*80}")
    
    test_date = df['game_date'].iloc[0]
    print(f"\nStored date: {test_date}")
    print(f"Type: {type(test_date)}")
    print(f"\nWhen sent to frontend as JSON:")
    print(f'  {{"game_date": "{test_date}"}}')
    print(f"\nJavaScript will display this as: {test_date}")
    print(f"  (No timezone conversion because there's no time component)")


if __name__ == "__main__":
    fix_game_dates()
