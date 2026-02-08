"""
Complete training pipeline for advanced points prediction.
Uses enhanced feature engineering + ensemble model.
Target: Reduce MAE from 6.01 to <6.0

Usage:
    python -m scripts.train_advanced_points
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import sqlite3
import logging
from pathlib import Path

from app.ml.points_feature_engineer import PointsFeatureEngineer
from app.ml.ensemble_points import EnsemblePointsPredictor

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_data(db_path: str = 'data/nba.db') -> pd.DataFrame:
    """Load game data from database"""
    logger.info("Loading data from database...")
    
    conn = sqlite3.connect(db_path)
    
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
    
    logger.info(f"Loaded {len(df)} game records for {df['player_id'].nunique()} players")
    return df


def main():
    """Main training pipeline"""
    print("=" * 70)
    print("ADVANCED POINTS PREDICTION MODEL TRAINING")
    print("Target: MAE < 6.0 (current: 6.01)")
    print("=" * 70)
    
    # Load data
    df = load_data()
    
    if len(df) < 500:
        logger.error(f"Insufficient data: {len(df)} rows. Need at least 500.")
        return
    
    # Phase 1: Feature Engineering
    print("\n" + "=" * 70)
    print("PHASE 1: ADVANCED FEATURE ENGINEERING")
    print("=" * 70)
    
    engineer = PointsFeatureEngineer()
    df_enhanced = engineer.create_all_features(df)
    
    # Print feature summary
    summary = engineer.get_feature_summary()
    print("\nFeature groups created:")
    for group, count in summary.items():
        print(f"  {group:20} {count:3} features")
    print(f"  {'TOTAL':20} {sum(summary.values()):3} features")
    
    # Get feature list
    features = engineer.get_feature_list()
    
    # Drop rows with NaN in core features
    core_features = ['pts_avg_5', 'pts_avg_10', 'season_pts_avg']
    df_clean = df_enhanced.dropna(subset=core_features)
    print(f"\nClean samples: {len(df_clean)} (dropped {len(df_enhanced) - len(df_clean)} with missing features)")
    
    # Phase 2: Train Ensemble
    print("\n" + "=" * 70)
    print("PHASE 2: ENSEMBLE MODEL TRAINING")
    print("=" * 70)
    
    ensemble = EnsemblePointsPredictor(models_dir='models')
    metrics = ensemble.train(df_clean, features)
    
    # Phase 3: Results Summary
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE - RESULTS SUMMARY")
    print("=" * 70)
    
    print("\nModel Performance:")
    print(f"  XGBoost MAE:     {metrics.get('xgb_mae', 'N/A'):.3f}" if 'xgb_mae' in metrics else "  XGBoost: Not trained")
    print(f"  LightGBM MAE:    {metrics.get('lgbm_mae', 'N/A'):.3f}" if 'lgbm_mae' in metrics else "  LightGBM: Not trained")
    print(f"  Ensemble MAE:    {metrics.get('ensemble_mae', 'N/A'):.3f}" if 'ensemble_mae' in metrics else "  Ensemble: Not evaluated")
    
    # Check success
    ensemble_mae = metrics.get('ensemble_mae', 999)
    
    print("\n" + "-" * 70)
    if ensemble_mae < 6.0:
        print(f"✅ SUCCESS! Ensemble MAE ({ensemble_mae:.3f}) < 6.0 target")
    else:
        print(f"⚠️  Ensemble MAE ({ensemble_mae:.3f}) >= 6.0 target")
        print("   Consider: more data, hyperparameter tuning, or additional features")
    print("-" * 70)
    
    # Compare to baseline
    baseline_mae = 6.01
    improvement = baseline_mae - ensemble_mae
    pct_improvement = (improvement / baseline_mae) * 100
    
    print(f"\nImprovement over baseline (6.01):")
    print(f"  Absolute: {improvement:+.3f} MAE")
    print(f"  Relative: {pct_improvement:+.1f}%")
    
    print("\n✓ Models saved to models/points_ensemble_model.joblib")


if __name__ == "__main__":
    main()
