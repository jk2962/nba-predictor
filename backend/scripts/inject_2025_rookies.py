
import pandas as pd
from pathlib import Path
from datetime import datetime

def inject_rookies():
    print("Injecting 2025 rookies...")
    
    rookies = [
        {'id': 2025001, 'name': 'Ace Bailey', 'position': 'SF'},
        {'id': 2025002, 'name': 'Cooper Flagg', 'position': 'PF'},
        {'id': 2025003, 'name': 'Dylan Harper', 'position': 'PG'},
        {'id': 2025004, 'name': 'V.J. Edgecombe', 'position': 'SG'},
        {'id': 2025005, 'name': 'Tre Johnson', 'position': 'SG'},
    ]
    
    # 1. Update Activity Stats
    activity_file = Path('backend/data/player_activity_stats.csv')
    if activity_file.exists():
        df = pd.read_csv(activity_file)
        
        new_rows = []
        for r in rookies:
            if r['id'] not in df['player_id'].values:
                new_rows.append({
                    'player_id': r['id'],
                    'player_name': r['name'],
                    'total_games': 0,
                    'last_game': None,
                    'avg_minutes': 0.0,
                    'days_since_last_game': 999,
                    'games_last_6_months': 0,
                    'is_active': False,
                    'activity_status': 'ROOKIE_2025'
                })
        
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            df.to_csv(activity_file, index=False)
            print(f"Added {len(new_rows)} rookies to activity stats")
            
    # 2. Update Game Logs (for DraftHelper visibility)
    logs_file = Path('backend/data/full_nba_game_logs.csv')
    if logs_file.exists():
        df_logs = pd.read_csv(logs_file)
        
        new_logs = []
        for r in rookies:
            if r['id'] not in df_logs['player_id'].values:
                # Add a dummy row so they appear in the system
                new_logs.append({
                    'player_id': r['id'],
                    'player_name': r['name'],
                    'season': '2025-26',
                    'game_date': datetime.now().strftime('%Y-%m-%d'),
                    'matchup': 'ROOKIE',
                    'win_loss': 'N/A',
                    'minutes': 0,
                    'points': 0,
                    'rebounds': 0,
                    'assists': 0,
                    'steals': 0,
                    'blocks': 0,
                    'turnovers': 0,
                    'plus_minus': 0,
                    'fantasy_points': 0,
                    'video_available': 0,
                    'home_game': 0,
                    'opponent': 'N/A'
                })
                
        if new_logs:
            # Align columns
            dummy_df = pd.DataFrame(new_logs)
            for col in df_logs.columns:
                if col not in dummy_df.columns:
                    dummy_df[col] = 0 # Default other cols to 0
            
            df_logs = pd.concat([df_logs, dummy_df], ignore_index=True)
            df_logs.to_csv(logs_file, index=False)
            print(f"Added {len(new_logs)} rookie entries to game logs")

if __name__ == "__main__":
    inject_rookies()
