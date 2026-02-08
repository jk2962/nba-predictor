"""
Automated fix for common model bugs.
Rebuilds entire training pipeline with validation at each step.

Usage:
    python -m scripts.auto_fix
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import joblib
from pathlib import Path
from datetime import datetime
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoFix:
    """Automatically rebuild models with proper safeguards"""
    
    def __init__(
        self, 
        db_path: str = 'data/nba.db',
        output_dir: str = 'models'
    ):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Position-based realistic bounds
        self.position_bounds = {
            'PG': {'points': (0, 50), 'rebounds': (0, 10), 'assists': (0, 18)},
            'SG': {'points': (0, 55), 'rebounds': (0, 12), 'assists': (0, 15)},
            'SF': {'points': (0, 50), 'rebounds': (0, 15), 'assists': (0, 12)},
            'PF': {'points': (0, 45), 'rebounds': (0, 20), 'assists': (0, 10)},
            'C': {'points': (0, 45), 'rebounds': (0, 25), 'assists': (0, 12)},
            'G': {'points': (0, 55), 'rebounds': (0, 12), 'assists': (0, 18)},
            'F': {'points': (0, 50), 'rebounds': (0, 18), 'assists': (0, 12)},
        }
        
    def load_data(self) -> pd.DataFrame:
        """Load and prepare training data"""
        logger.info("Loading data from database...")
        
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                p.id as player_id,
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
            ORDER BY p.id, g.game_date
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        logger.info(f"Loaded {len(df)} game records")
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create rolling features for each player"""
        logger.info("Creating features...")
        
        all_player_dfs = []
        
        for player_id in df['player_id'].unique():
            player_df = df[df['player_id'] == player_id].copy()
            player_df = player_df.sort_values('game_date')
            
            # Rolling averages (SHIFTED to prevent leakage)
            for window in [5, 10, 15]:
                for col, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                                   ('assists', 'ast'), ('minutes', 'min')]:
                    if col in player_df.columns:
                        player_df[f'{prefix}_avg_{window}'] = player_df[col].rolling(
                            window=window, min_periods=1
                        ).mean().shift(1)
            
            # Season averages (expanding mean, SHIFTED)
            for col, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                               ('assists', 'ast'), ('minutes', 'min')]:
                if col in player_df.columns:
                    player_df[f'season_{prefix}_avg'] = player_df[col].expanding().mean().shift(1)
            
            # Shooting percentages rolling (SHIFTED)
            for col in ['fg_pct', 'fg3_pct', 'ft_pct']:
                if col in player_df.columns:
                    player_df[f'{col}_avg_10'] = player_df[col].rolling(
                        window=10, min_periods=1
                    ).mean().shift(1)
            
            all_player_dfs.append(player_df)
        
        result = pd.concat(all_player_dfs, ignore_index=True)
        logger.info(f"Created features for {len(df['player_id'].unique())} players")
        return result
    
    def get_target_features(self, target: str) -> list:
        """Get isolated feature set for a specific target"""
        
        # Base features for all targets
        base = ['is_home', 'rest_days']
        
        # Target-specific features
        target_map = {
            'points': [
                'pts_avg_5', 'pts_avg_10', 'pts_avg_15',
                'min_avg_5', 'min_avg_10',
                'season_pts_avg', 'season_min_avg',
                'fg_pct_avg_10', 'fg3_pct_avg_10', 'ft_pct_avg_10',
            ],
            'rebounds': [
                'reb_avg_5', 'reb_avg_10', 'reb_avg_15',
                'min_avg_5', 'min_avg_10',
                'season_reb_avg', 'season_min_avg',
            ],
            'assists': [
                'ast_avg_5', 'ast_avg_10', 'ast_avg_15',
                'min_avg_5', 'min_avg_10',
                'season_ast_avg', 'season_min_avg',
            ],
        }
        
        return base + target_map.get(target, [])
    
    def rebuild_all_models(self):
        """Complete rebuild of all models with validation"""
        logger.info("=" * 60)
        logger.info("AUTOMATED MODEL REBUILD")
        logger.info("=" * 60)
        
        # Load and prepare data
        df = self.load_data()
        
        if len(df) < 100:
            logger.error(f"Insufficient data: {len(df)} rows")
            return
        
        # Create features
        df = self.create_features(df)
        
        # Drop rows with NaN in first games
        initial_rows = len(df)
        df = df.dropna(subset=['pts_avg_5', 'reb_avg_5', 'ast_avg_5'])
        logger.info(f"Dropped {initial_rows - len(df)} rows with missing rolling averages")
        
        results = {}
        
        for target in ['points', 'rebounds', 'assists']:
            logger.info("\n" + "=" * 60)
            logger.info(f"Training {target.upper()} model")
            logger.info("=" * 60)
            
            try:
                metrics = self.build_target_model(df, target)
                results[target] = metrics
            except Exception as e:
                logger.error(f"Failed to train {target} model: {e}")
                import traceback
                traceback.print_exc()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("REBUILD COMPLETE")
        logger.info("=" * 60)
        
        for target, m in results.items():
            logger.info(f"{target.capitalize():10} MAE: {m['mae']:.3f}, R²: {m['r2']:.3f}")
        
        # Save combined metrics
        joblib.dump(results, self.output_dir / 'metrics.joblib')
        
        return results
    
    def build_target_model(self, df: pd.DataFrame, target: str) -> dict:
        """Build model for a single target with full validation"""
        
        # Get target-specific features
        feature_names = self.get_target_features(target)
        
        # Filter to available features
        available = [f for f in feature_names if f in df.columns]
        logger.info(f"Features: {len(available)}/{len(feature_names)} available")
        logger.info(f"Using: {available}")
        
        if len(available) < 3:
            raise ValueError(f"Not enough features available for {target}")
        
        # Prepare data
        df_clean = df.dropna(subset=[target] + available)
        logger.info(f"Training samples: {len(df_clean)}")
        
        X = df_clean[available]
        y = df_clean[target]
        
        # CRITICAL: Verify target is not in features
        if target in available:
            raise ValueError(f"Target '{target}' found in feature list - LEAKAGE!")
        
        # Time-based split
        if 'game_date' in df_clean.columns:
            df_sorted = df_clean.sort_values('game_date')
            split_idx = int(len(df_sorted) * 0.8)
            
            train_idx = df_sorted.index[:split_idx]
            test_idx = df_sorted.index[split_idx:]
            
            X_train = X.loc[train_idx]
            X_test = X.loc[test_idx]
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Train model
        model = XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"Test MAE: {mae:.3f}")
        logger.info(f"Test R²:  {r2:.3f}")
        
        # Sanity check predictions
        logger.info("\nPrediction sanity check:")
        logger.info(f"  Actual - mean: {y_test.mean():.2f}, std: {y_test.std():.2f}")
        logger.info(f"  Pred   - mean: {y_pred.mean():.2f}, std: {y_pred.std():.2f}")
        
        # Check for unrealistic predictions
        neg_preds = (y_pred < 0).sum()
        if neg_preds > 0:
            logger.warning(f"  ⚠️ {neg_preds} negative predictions")
        
        # Save model with metadata
        model_package = {
            'model': model,
            'features': available,
            'target': target,
            'mae': mae,
            'r2': r2,
            'version': '2.1.0_autofix',
            'trained_at': datetime.now().isoformat(),
            'position_bounds': self.position_bounds,
        }
        
        filepath = self.output_dir / f'{target}_model.joblib'
        joblib.dump(model_package, filepath)
        logger.info(f"✓ Saved to {filepath}")
        
        return {'mae': mae, 'r2': r2, 'samples': len(X_train)}


def main():
    fixer = AutoFix(
        db_path='data/nba.db',
        output_dir='models'
    )
    fixer.rebuild_all_models()


if __name__ == "__main__":
    main()
