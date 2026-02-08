"""
Retrain models with expanded dataset.
Run after collect_full_nba_dataset.py completes.

Usage:
    python -m scripts.retrain_with_expanded_data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from datetime import datetime
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_expanded_data(data_path: str = 'data/full_nba_game_logs.csv') -> pd.DataFrame:
    """Load the expanded dataset."""
    logger.info(f"Loading expanded dataset from {data_path}...")
    
    if not Path(data_path).exists():
        logger.error(f"Dataset not found: {data_path}")
        logger.error("Run 'python -m scripts.collect_full_nba_dataset' first!")
        return pd.DataFrame()
    
    df = pd.read_csv(data_path)
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    logger.info(f"Loaded {len(df):,} games for {df['player_id'].nunique()} players")
    return df


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create rolling features for prediction."""
    logger.info("Creating features...")
    
    df = df.sort_values(['player_id', 'game_date']).copy()
    
    # Rolling averages (SHIFTED to prevent leakage)
    for stat, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                         ('assists', 'ast'), ('minutes', 'min')]:
        if stat in df.columns:
            for window in [5, 10, 15]:
                df[f'{prefix}_avg_{window}'] = df.groupby('player_id')[stat].transform(
                    lambda x: x.rolling(window, min_periods=1).mean().shift(1)
                )
    
    # Shooting percentages
    for col in ['fg_pct', 'fg3_pct', 'ft_pct']:
        if col in df.columns:
            df[f'{col}_avg_10'] = df.groupby('player_id')[col].transform(
                lambda x: x.rolling(10, min_periods=1).mean().shift(1)
            )
    
    # Season averages
    for stat, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                         ('assists', 'ast'), ('minutes', 'min')]:
        if stat in df.columns:
            df[f'season_{prefix}_avg'] = df.groupby('player_id')[stat].transform(
                lambda x: x.expanding().mean().shift(1)
            )
    
    # Fill missing values
    if 'is_home' not in df.columns:
        df['is_home'] = 1
    if 'rest_days' not in df.columns:
        df['rest_days'] = 2
    
    df['opponent_def_rating'] = 110.0
    
    return df


def train_model(df: pd.DataFrame, target: str, features: list) -> dict:
    """Train a single model for a target."""
    
    # Clean data
    available = [f for f in features if f in df.columns]
    df_clean = df.dropna(subset=[target] + available[:5])
    
    if len(df_clean) < 1000:
        logger.warning(f"Insufficient data for {target}: {len(df_clean)}")
        return None
    
    X = df_clean[available].fillna(0)
    y = df_clean[target]
    
    # Time-based split
    split_idx = int(len(df_clean) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    # Train
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
    
    return {
        'model': model,
        'features': available,
        'mae': mae,
        'r2': r2,
        'n_train': len(X_train),
        'n_test': len(X_test)
    }


def main():
    logger.info("="*70)
    logger.info("    RETRAINING MODELS WITH EXPANDED DATASET")
    logger.info("="*70)
    
    # Load data
    df = load_expanded_data()
    
    if len(df) == 0:
        return
    
    # Create features
    df = create_features(df)
    
    # Define feature sets
    feature_sets = {
        'points': [
            'pts_avg_5', 'pts_avg_10', 'pts_avg_15',
            'min_avg_5', 'min_avg_10',
            'season_pts_avg', 'season_min_avg',
            'fg_pct_avg_10', 'fg3_pct_avg_10', 'ft_pct_avg_10',
            'is_home', 'rest_days', 'opponent_def_rating',
        ],
        'rebounds': [
            'reb_avg_5', 'reb_avg_10', 'reb_avg_15',
            'min_avg_5', 'min_avg_10',
            'season_reb_avg', 'season_min_avg',
            'is_home', 'rest_days', 'opponent_def_rating',
        ],
        'assists': [
            'ast_avg_5', 'ast_avg_10', 'ast_avg_15',
            'min_avg_5', 'min_avg_10',
            'season_ast_avg', 'season_min_avg',
            'is_home', 'rest_days', 'opponent_def_rating',
        ],
    }
    
    # Train models
    logger.info("\n" + "="*70)
    logger.info("TRAINING MODELS")
    logger.info("="*70)
    
    results = {}
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    
    for target, features in feature_sets.items():
        logger.info(f"\n[{target.upper()}]")
        
        result = train_model(df, target, features)
        
        if result:
            results[target] = result
            
            # Save model
            model_package = {
                'model': result['model'],
                'features': result['features'],
                'target': target,
                'version': '3.0.0_expanded',
                'trained_at': datetime.now().isoformat(),
                'n_players': df['player_id'].nunique(),
                'n_games': len(df),
            }
            
            model_path = models_dir / f'{target}_model.joblib'
            joblib.dump(model_package, model_path)
            
            logger.info(f"  MAE: {result['mae']:.3f}")
            logger.info(f"  R²:  {result['r2']:.3f}")
            logger.info(f"  ✓ Saved to {model_path}")
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("TRAINING SUMMARY")
    logger.info("="*70)
    
    logger.info(f"\nDataset: {df['player_id'].nunique()} players, {len(df):,} games\n")
    
    for target, r in results.items():
        logger.info(f"{target.capitalize():10} MAE: {r['mae']:.3f}, R²: {r['r2']:.3f}")
    
    # Save metrics
    metrics = {
        target: {'mae': r['mae'], 'r2': r['r2']}
        for target, r in results.items()
    }
    joblib.dump(metrics, models_dir / 'metrics.joblib')
    
    logger.info("\n✓ All models saved to models/")
    logger.info("\nRestart the server to load new models:")
    logger.info("  ./restart-servers.sh")


if __name__ == "__main__":
    main()
