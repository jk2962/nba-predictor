"""
Emergency diagnostic for model prediction bugs.
Tests: data integrity, model files, feature sets, prediction pipeline.
Run this BEFORE attempting any fixes.

Usage:
    python -m scripts.emergency_diagnostic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')


class EmergencyDiagnostic:
    """Comprehensive diagnostic for model bugs"""
    
    def __init__(self, models_dir: str = 'models', db_path: str = 'data/nba.db'):
        self.models_dir = Path(models_dir)
        self.db_path = db_path
        self.issues_found = []
        
    def run_all_checks(self):
        """Run complete diagnostic suite"""
        print("=" * 80)
        print(" " * 20 + "EMERGENCY MODEL DIAGNOSTIC")
        print("=" * 80)
        
        df = self.load_data()
        
        if df is not None and len(df) > 0:
            self.check_1_data_integrity(df)
            self.check_2_model_files()
            self.check_3_training_data_distributions(df)
            self.check_4_known_player_sanity(df)
            self.check_5_prediction_pipeline(df)
            self.check_6_feature_contamination(df)
        else:
            self.check_2_model_files()
        
        self.print_summary()
        
    def load_data(self) -> Optional[pd.DataFrame]:
        """Load training data from database"""
        print("\n[STEP 1] Loading training data...")
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            
            # Load player stats with game info
            query = """
                SELECT 
                    p.name as player_name,
                    p.position,
                    p.team,
                    g.game_date,
                    ps.points,
                    ps.rebounds,
                    ps.assists,
                    ps.minutes,
                    ps.steals,
                    ps.blocks,
                    ps.turnovers,
                    ps.fg_pct,
                    ps.fg3_pct,
                    ps.ft_pct,
                    ps.is_home,
                    ps.rest_days
                FROM player_stats ps
                JOIN players p ON ps.player_id = p.id
                JOIN games g ON ps.game_id = g.id
                ORDER BY g.game_date
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            print(f"✓ Loaded {len(df)} rows from database")
            print(f"✓ Columns: {list(df.columns)}")
            return df
            
        except Exception as e:
            print(f"⚠️ Could not load from database: {e}")
            
            # Try CSV fallback
            csv_path = Path('data/training_data.csv')
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    print(f"✓ Loaded {len(df)} rows from CSV")
                    return df
                except Exception as e2:
                    print(f"🚨 Failed to load CSV: {e2}")
            
            print("⚠️ No training data available - will check model files only")
            return None
    
    def check_1_data_integrity(self, df: pd.DataFrame):
        """Check if raw training data has sane values"""
        print("\n" + "=" * 80)
        print("[CHECK 1] DATA INTEGRITY")
        print("=" * 80)
        
        required_cols = ['points', 'rebounds', 'assists']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            issue = f"Missing required columns: {missing_cols}"
            print(f"🚨 {issue}")
            self.issues_found.append(issue)
            return
        
        print("\n✓ All required columns present")
        
        # Check target distributions
        print("\nTarget variable statistics:")
        stats_df = df[['points', 'rebounds', 'assists']].describe()
        print(stats_df)
        
        # Sanity checks
        issues = []
        
        # Points checks
        if df['points'].mean() < 5:
            issues.append(f"Points mean ({df['points'].mean():.1f}) suspiciously low")
        if df['points'].mean() > 25:
            issues.append(f"Points mean ({df['points'].mean():.1f}) suspiciously high")
        if df['points'].max() > 100:
            issues.append(f"Points max ({df['points'].max():.1f}) impossible")
        
        # Rebounds checks
        if df['rebounds'].mean() > 12:
            issues.append(f"Rebounds mean ({df['rebounds'].mean():.1f}) suspiciously high")
        if df['rebounds'].max() > 40:
            issues.append(f"Rebounds max ({df['rebounds'].max():.1f}) impossible")
        
        # Assists checks
        if df['assists'].mean() > 10:
            issues.append(f"Assists mean ({df['assists'].mean():.1f}) suspiciously high")
        if df['assists'].max() > 30:
            issues.append(f"Assists max ({df['assists'].max():.1f}) impossible")
        
        # Negative values
        for col in ['points', 'rebounds', 'assists']:
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                issues.append(f"{col}: {neg_count} negative values")
        
        # Position-based sanity
        if 'position' in df.columns:
            print("\nPosition-based averages:")
            position_stats = df.groupby('position')[['points', 'rebounds', 'assists']].mean()
            print(position_stats)
            
            # Guards shouldn't average 15 rebounds
            for pos in ['PG', 'SG', 'G']:
                if pos in position_stats.index:
                    pg_reb = position_stats.loc[pos, 'rebounds']
                    if pg_reb > 8:
                        issues.append(f"{pos} averaging {pg_reb:.1f} rebounds (expected 3-5)")
            
            # Centers shouldn't average 12 assists
            if 'C' in position_stats.index:
                c_ast = position_stats.loc['C', 'assists']
                if c_ast > 8:
                    issues.append(f"C averaging {c_ast:.1f} assists (expected 1-4)")
        
        if issues:
            print("\n🚨 Data integrity issues found:")
            for issue in issues:
                print(f"  • {issue}")
            self.issues_found.extend(issues)
        else:
            print("\n✓ Data integrity checks passed")
    
    def check_2_model_files(self):
        """Check model files exist and contain correct metadata"""
        print("\n" + "=" * 80)
        print("[CHECK 2] MODEL FILES")
        print("=" * 80)
        
        for target in ['points', 'rebounds', 'assists']:
            print(f"\n--- {target.upper()} Model ---")
            
            filepath = self.models_dir / f'{target}_model.joblib'
            
            if not filepath.exists():
                issue = f"{target} model file not found at {filepath}"
                print(f"🚨 {issue}")
                self.issues_found.append(issue)
                continue
            
            print(f"✓ File exists: {filepath}")
            
            try:
                loaded = joblib.load(filepath)
                
                # Check structure
                if isinstance(loaded, dict):
                    print(f"  File structure: dictionary")
                    print(f"  Keys: {list(loaded.keys())}")
                    
                    # Check if it has target metadata
                    if 'target' in loaded:
                        claimed_target = loaded['target']
                        if claimed_target != target:
                            issue = f"{target}_model.joblib claims to be '{claimed_target}' model (FILE MISMATCH!)"
                            print(f"  🚨 {issue}")
                            self.issues_found.append(issue)
                        else:
                            print(f"  ✓ Target metadata correct: '{claimed_target}'")
                    else:
                        print(f"  ⚠️  No 'target' metadata in file")
                    
                    # Check version
                    if 'version' in loaded:
                        print(f"  Version: {loaded['version']}")
                    
                    # Check features
                    if 'features' in loaded:
                        features = loaded['features']
                        print(f"  Features: {len(features)} total")
                        
                        # Look for target-related features
                        target_features = [f for f in features if target[:3] in f.lower()]
                        print(f"  Features for '{target}': {len(target_features)}")
                        if target_features[:5]:
                            print(f"    Examples: {target_features[:5]}")
                        
                        # Check for WRONG target features (major bug)
                        target_prefixes = {'points': 'pts', 'rebounds': 'reb', 'assists': 'ast'}
                        for wrong_target, wrong_prefix in target_prefixes.items():
                            if wrong_target == target:
                                continue
                            
                            wrong_features = [f for f in features if wrong_prefix in f.lower() and 'opponent' not in f.lower()]
                            if len(wrong_features) > 3:
                                issue = f"{target} model has {len(wrong_features)} '{wrong_target}' features"
                                print(f"  ⚠️  {issue}")
                                print(f"    Examples: {wrong_features[:3]}")
                    else:
                        print(f"  ⚠️  No 'features' list in file")
                    
                    # Check model object
                    if 'model' in loaded:
                        model = loaded['model']
                        print(f"  Model type: {type(model).__name__}")
                    else:
                        print(f"  🚨 No 'model' object in file")
                
                else:
                    print(f"  File structure: bare model object")
                    print(f"  Model type: {type(loaded).__name__}")
                    print(f"  ⚠️  No metadata (features, target) stored")
                    
            except Exception as e:
                issue = f"Failed to load {target} model: {e}"
                print(f"🚨 {issue}")
                self.issues_found.append(issue)
    
    def check_3_training_data_distributions(self, df: pd.DataFrame):
        """Check if training data looks normal"""
        print("\n" + "=" * 80)
        print("[CHECK 3] TRAINING DATA DISTRIBUTIONS")
        print("=" * 80)
        
        for target in ['points', 'rebounds', 'assists']:
            if target not in df.columns:
                continue
            
            print(f"\n{target.upper()}:")
            values = df[target].dropna()
            
            print(f"  Count: {len(values)}")
            print(f"  Mean: {values.mean():.2f}")
            print(f"  Median: {values.median():.2f}")
            print(f"  Std: {values.std():.2f}")
            print(f"  Min: {values.min():.2f}")
            print(f"  Max: {values.max():.2f}")
            print(f"  25th pct: {values.quantile(0.25):.2f}")
            print(f"  75th pct: {values.quantile(0.75):.2f}")
            print(f"  95th pct: {values.quantile(0.95):.2f}")
    
    def check_4_known_player_sanity(self, df: pd.DataFrame):
        """Check if specific known players have sane stats"""
        print("\n" + "=" * 80)
        print("[CHECK 4] KNOWN PLAYER SANITY CHECKS")
        print("=" * 80)
        
        # Test cases with expected ranges
        test_players = [
            {
                'name': 'Trae Young',
                'position': 'PG',
                'expected': {
                    'points': (20, 32),
                    'rebounds': (2, 5),
                    'assists': (9, 13)
                }
            },
            {
                'name': 'Nikola Jokic',
                'position': 'C',
                'expected': {
                    'points': (20, 30),
                    'rebounds': (10, 16),
                    'assists': (7, 11)
                }
            },
            {
                'name': 'Stephen Curry',
                'position': 'PG',
                'expected': {
                    'points': (24, 32),
                    'rebounds': (3, 6),
                    'assists': (5, 8)
                }
            },
        ]
        
        if 'player_name' not in df.columns:
            print("⚠️  'player_name' column not found, skipping")
            return
        
        for player_info in test_players:
            name = player_info['name']
            expected_pos = player_info['position']
            expected = player_info['expected']
            
            player_data = df[df['player_name'] == name]
            
            if len(player_data) == 0:
                print(f"\n{name}: Not found in dataset")
                continue
            
            print(f"\n{name} ({expected_pos}):")
            print(f"  Games in dataset: {len(player_data)}")
            
            if 'position' in player_data.columns:
                actual_pos = player_data['position'].mode()[0]
                print(f"  Position in data: {actual_pos}")
            
            for stat, (min_exp, max_exp) in expected.items():
                if stat not in player_data.columns:
                    continue
                
                avg = player_data[stat].mean()
                print(f"  {stat}: {avg:.1f} (expected {min_exp}-{max_exp})", end="")
                
                if avg < min_exp or avg > max_exp:
                    issue = f"{name}'s {stat} average ({avg:.1f}) outside expected range"
                    print(f" 🚨")
                    self.issues_found.append(issue)
                else:
                    print(f" ✓")
    
    def check_5_prediction_pipeline(self, df: pd.DataFrame):
        """Test actual predictions on known players"""
        print("\n" + "=" * 80)
        print("[CHECK 5] PREDICTION PIPELINE TEST")
        print("=" * 80)
        
        # Load models
        models = {}
        features_dict = {}
        
        for target in ['points', 'rebounds', 'assists']:
            filepath = self.models_dir / f'{target}_model.joblib'
            
            if not filepath.exists():
                continue
            
            try:
                loaded = joblib.load(filepath)
                if isinstance(loaded, dict):
                    models[target] = loaded.get('model')
                    features_dict[target] = loaded.get('features', [])
                else:
                    models[target] = loaded
                    features_dict[target] = []
            except:
                continue
        
        if not models:
            print("🚨 No models could be loaded")
            return
        
        print(f"\n✓ Loaded {len(models)} models")
        
        # Need training data with features
        if 'player_name' not in df.columns:
            print("\n⚠️  Cannot test predictions - no player_name column")
            return
        
        # Try to find a guard to test
        guards = df[df['position'].isin(['PG', 'SG', 'G'])] if 'position' in df.columns else pd.DataFrame()
        
        if len(guards) > 0:
            test_row = guards.iloc[-1]
            player_name = test_row.get('player_name', 'Unknown Guard')
            position = test_row.get('position', 'G')
        else:
            test_row = df.iloc[-1]
            player_name = test_row.get('player_name', 'Unknown')
            position = test_row.get('position', 'Unknown')
        
        print(f"\nTesting predictions for: {player_name} ({position})")
        print(f"Actual stats from data:")
        print(f"  Points: {test_row.get('points', 'N/A')}")
        print(f"  Rebounds: {test_row.get('rebounds', 'N/A')}")
        print(f"  Assists: {test_row.get('assists', 'N/A')}")
        
        print(f"\nModel predictions:")
        
        for target, model in models.items():
            if model is None:
                print(f"  {target}: Model is None")
                continue
            
            features = features_dict.get(target, [])
            
            if not features:
                print(f"  {target}: No features list available")
                continue
            
            # Check available features
            missing = [f for f in features if f not in test_row.index]
            if len(missing) > len(features) * 0.5:
                print(f"  {target}: Missing {len(missing)}/{len(features)} features")
                continue
            
            try:
                available_features = [f for f in features if f in test_row.index]
                X = test_row[available_features].values.reshape(1, -1)
                pred = model.predict(X)[0]
                actual = test_row.get(target, 'N/A')
                
                print(f"  {target}: {pred:.1f} (actual: {actual})", end="")
                
                # Sanity check for guards
                is_guard = position in ['PG', 'SG', 'G']
                
                if target == 'rebounds' and is_guard and pred > 12:
                    issue = f"Guard predicted to get {pred:.1f} rebounds (UNREALISTIC!)"
                    print(f" 🚨 {issue}")
                    self.issues_found.append(issue)
                elif target == 'assists' and is_guard and pred < 3 and (isinstance(actual, (int, float)) and actual > 8):
                    issue = f"Guard predicted only {pred:.1f} assists (actual avg {actual})"
                    print(f" 🚨 {issue}")
                    self.issues_found.append(issue)
                else:
                    print(" ✓")
                
            except Exception as e:
                print(f"  {target}: Error - {e}")
    
    def check_6_feature_contamination(self, df: pd.DataFrame):
        """Check if features accidentally include target variables"""
        print("\n" + "=" * 80)
        print("[CHECK 6] FEATURE-TARGET CONTAMINATION")
        print("=" * 80)
        
        for target in ['points', 'rebounds', 'assists']:
            filepath = self.models_dir / f'{target}_model.joblib'
            
            if not filepath.exists():
                continue
            
            try:
                loaded = joblib.load(filepath)
                if isinstance(loaded, dict) and 'features' in loaded:
                    features = loaded['features']
                else:
                    print(f"\n{target}: No feature list available")
                    continue
                
                print(f"\n{target.upper()} model features ({len(features)} total):")
                
                # Check if target itself is in features
                if target in features:
                    issue = f"{target} model has '{target}' as a feature (DIRECT LEAKAGE!)"
                    print(f"  🚨 {issue}")
                    self.issues_found.append(issue)
                
                # Show correlation if data available
                if target in df.columns:
                    high_corr = []
                    for feature in features:
                        if feature in df.columns:
                            try:
                                corr = df[feature].corr(df[target])
                                if abs(corr) > 0.99:
                                    high_corr.append((feature, corr))
                            except:
                                pass
                    
                    if high_corr:
                        print(f"  🚨 Features with correlation > 0.99 (LEAKAGE!):")
                        for feat, corr in high_corr[:5]:
                            print(f"    • {feat}: {corr:.4f}")
                            self.issues_found.append(f"High correlation: {feat} -> {target}")
                
            except Exception as e:
                print(f"\n{target}: Error checking features - {e}")
    
    def print_summary(self):
        """Print summary of all issues found"""
        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        if not self.issues_found:
            print("\n✓ No critical issues detected!")
            print("\nIf predictions are still wrong, check:")
            print("  1. How features are prepared for prediction")
            print("  2. Model file loading order")
            print("  3. Feature preprocessing (scaling, encoding)")
        else:
            print(f"\n🚨 Found {len(self.issues_found)} issues:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"\n{i}. {issue}")
            
            print("\n" + "=" * 80)
            print("RECOMMENDED FIXES:")
            print("=" * 80)
            
            if any('MISMATCH' in issue or 'SWAPPED' in issue for issue in self.issues_found):
                print("\n🔧 MODEL SWAP/MISMATCH DETECTED:")
                print("   → Retrain all models with proper labeling")
                print("   → Run: python -m scripts.auto_fix")
            
            if any('LEAKAGE' in issue or 'correlation' in issue.lower() for issue in self.issues_found):
                print("\n🔧 DATA LEAKAGE DETECTED:")
                print("   → Rebuild feature engineering to exclude same-game stats")
                print("   → Ensure all features use .shift(1)")


def main():
    diagnostic = EmergencyDiagnostic(
        models_dir='models',
        db_path='data/nba.db'
    )
    diagnostic.run_all_checks()


if __name__ == "__main__":
    main()
