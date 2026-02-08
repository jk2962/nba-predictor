"""
Ensemble points predictor combining multiple models.
Uses XGBoost + LightGBM + archetype-specific models.
Target: MAE < 6.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import joblib
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Try to import LightGBM, fall back to XGBoost if not available
HAS_LIGHTGBM = False
LGBMRegressor = None
try:
    from lightgbm import LGBMRegressor
    HAS_LIGHTGBM = True
except (ImportError, OSError):
    logger.warning("LightGBM not available, using XGBoost only")


class EnsemblePointsPredictor:
    """
    Ensemble of multiple prediction strategies for points.
    Combines XGBoost, LightGBM, and archetype-specific models.
    """
    
    def __init__(self, models_dir: str = 'models'):
        self.models_dir = Path(models_dir)
        
        # Model components
        self.xgb_model = None
        self.lgbm_model = None
        self.star_model = None   # For high scorers (>25 PPG)
        self.role_model = None   # For role players (<15 PPG)
        
        # Feature list
        self.features = []
        
        # Ensemble weights (optimized on validation)
        self.weights = {
            'xgb': 0.4,
            'lgbm': 0.4,
            'archetype': 0.2
        }
        
        # Metrics
        self.metrics = {}
        
    def train(self, df: pd.DataFrame, features: List[str]) -> Dict[str, float]:
        """
        Train all ensemble components.
        
        Args:
            df: DataFrame with features and 'points' target
            features: List of feature column names
            
        Returns:
            Dictionary with metrics
        """
        logger.info("=" * 60)
        logger.info("ENSEMBLE POINTS MODEL TRAINING")
        logger.info("=" * 60)
        
        self.features = features
        
        # Filter to available features
        available = [f for f in features if f in df.columns]
        logger.info(f"Using {len(available)}/{len(features)} features")
        
        # Prepare data
        df_clean = df.dropna(subset=['points'] + available[:10])  # Require core features
        logger.info(f"Training samples: {len(df_clean)}")
        
        # Handle categorical
        X = df_clean[available].copy()
        y = df_clean['points'].copy()
        
        # One-hot encode position
        if 'position' in X.columns:
            X = pd.get_dummies(X, columns=['position'], prefix='pos')
        
        # Handle any remaining categoricals
        for col in X.select_dtypes(include=['object']).columns:
            X = pd.get_dummies(X, columns=[col])
        
        # Fill NaN with median
        X = X.fillna(X.median())
        
        self.features = list(X.columns)
        
        # Time-based split (80/20)
        if 'game_date' in df_clean.columns:
            df_sorted = df_clean.sort_values('game_date')
            split_idx = int(len(df_sorted) * 0.8)
            train_idx = df_sorted.index[:split_idx]
            test_idx = df_sorted.index[split_idx:]
        else:
            train_idx, test_idx = train_test_split(
                df_clean.index, test_size=0.2, random_state=42
            )
        
        X_train, X_test = X.loc[train_idx], X.loc[test_idx]
        y_train, y_test = y.loc[train_idx], y.loc[test_idx]
        
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Train component models
        self._train_xgb(X_train, y_train, X_test, y_test)
        
        if HAS_LIGHTGBM:
            self._train_lgbm(X_train, y_train, X_test, y_test)
        
        # Train archetype models
        self._train_archetype_models(df_clean, X, y, available)
        
        # Evaluate ensemble
        ensemble_mae = self._evaluate_ensemble(X_test, y_test, df_clean.loc[test_idx])
        
        # Save models
        self._save_models()
        
        return self.metrics
    
    def _train_xgb(self, X_train, y_train, X_test, y_test):
        """Train XGBoost model"""
        logger.info("\n[1/4] Training XGBoost model...")
        
        self.xgb_model = XGBRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.03,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1
        )
        
        self.xgb_model.fit(X_train, y_train)
        
        y_pred = self.xgb_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        self.metrics['xgb_mae'] = mae
        self.metrics['xgb_r2'] = r2
        logger.info(f"  XGBoost MAE: {mae:.3f}, R²: {r2:.3f}")
    
    def _train_lgbm(self, X_train, y_train, X_test, y_test):
        """Train LightGBM model"""
        logger.info("\n[2/4] Training LightGBM model...")
        
        self.lgbm_model = LGBMRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.03,
            num_leaves=63,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        
        self.lgbm_model.fit(X_train, y_train)
        
        y_pred = self.lgbm_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        self.metrics['lgbm_mae'] = mae
        self.metrics['lgbm_r2'] = r2
        logger.info(f"  LightGBM MAE: {mae:.3f}, R²: {r2:.3f}")
    
    def _train_archetype_models(self, df, X, y, features):
        """Train archetype-specific models for stars and role players"""
        logger.info("\n[3/4] Training archetype models...")
        
        # Star scorer model (high PPG players)
        if 'season_pts_avg' in df.columns:
            stars_mask = df['season_pts_avg'] > 25
            if stars_mask.sum() > 100:
                X_stars = X.loc[stars_mask]
                y_stars = y.loc[stars_mask]
                
                # Simple split
                split = int(len(X_stars) * 0.8)
                X_train_s, X_test_s = X_stars.iloc[:split], X_stars.iloc[split:]
                y_train_s, y_test_s = y_stars.iloc[:split], y_stars.iloc[split:]
                
                self.star_model = XGBRegressor(
                    n_estimators=150,
                    max_depth=6,
                    learning_rate=0.05,
                    random_state=42,
                    n_jobs=-1
                )
                self.star_model.fit(X_train_s, y_train_s)
                
                mae = mean_absolute_error(y_test_s, self.star_model.predict(X_test_s))
                logger.info(f"  Star model MAE: {mae:.3f} (n={len(X_stars)})")
            else:
                logger.info(f"  Not enough star players for dedicated model")
        
        # Role player model (low PPG players)
        if 'season_pts_avg' in df.columns:
            role_mask = df['season_pts_avg'] < 15
            if role_mask.sum() > 100:
                X_role = X.loc[role_mask]
                y_role = y.loc[role_mask]
                
                split = int(len(X_role) * 0.8)
                X_train_r, X_test_r = X_role.iloc[:split], X_role.iloc[split:]
                y_train_r, y_test_r = y_role.iloc[:split], y_role.iloc[split:]
                
                self.role_model = XGBRegressor(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.05,
                    random_state=42,
                    n_jobs=-1
                )
                self.role_model.fit(X_train_r, y_train_r)
                
                mae = mean_absolute_error(y_test_r, self.role_model.predict(X_test_r))
                logger.info(f"  Role model MAE: {mae:.3f} (n={len(X_role)})")
            else:
                logger.info(f"  Not enough role players for dedicated model")
    
    def _evaluate_ensemble(self, X_test, y_test, df_test) -> float:
        """Evaluate ensemble prediction"""
        logger.info("\n[4/4] Evaluating ensemble...")
        
        predictions = []
        
        for idx in X_test.index:
            row = X_test.loc[[idx]]
            
            # Get player type
            ppg = df_test.loc[idx, 'season_pts_avg'] if 'season_pts_avg' in df_test.columns else None
            
            pred = self.predict(row, player_avg_ppg=ppg)
            predictions.append(pred)
        
        ensemble_mae = mean_absolute_error(y_test, predictions)
        ensemble_r2 = r2_score(y_test, predictions)
        
        self.metrics['ensemble_mae'] = ensemble_mae
        self.metrics['ensemble_r2'] = ensemble_r2
        
        logger.info(f"\n{'='*60}")
        logger.info(f"ENSEMBLE POINTS MAE: {ensemble_mae:.3f}")
        logger.info(f"ENSEMBLE POINTS R²:  {ensemble_r2:.3f}")
        logger.info(f"{'='*60}")
        
        # Compare to individual models
        if 'xgb_mae' in self.metrics:
            improvement = self.metrics['xgb_mae'] - ensemble_mae
            logger.info(f"Improvement over XGB: {improvement:.3f}")
        
        return ensemble_mae
    
    def predict(
        self, 
        features: pd.DataFrame, 
        player_avg_ppg: Optional[float] = None
    ) -> float:
        """
        Make ensemble prediction for points.
        
        Args:
            features: DataFrame with feature values (single row)
            player_avg_ppg: Player's season average PPG (for archetype selection)
            
        Returns:
            Predicted points
        """
        predictions = []
        weights = []
        
        # Ensure features match training features
        missing = [f for f in self.features if f not in features.columns]
        if missing:
            for f in missing:
                features[f] = 0
        
        features = features[self.features]
        
        # XGBoost prediction
        if self.xgb_model:
            pred_xgb = self.xgb_model.predict(features)[0]
            predictions.append(pred_xgb)
            weights.append(self.weights['xgb'])
        
        # LightGBM prediction
        if self.lgbm_model:
            pred_lgbm = self.lgbm_model.predict(features)[0]
            predictions.append(pred_lgbm)
            weights.append(self.weights['lgbm'])
        
        # Archetype prediction
        archetype_pred = None
        if player_avg_ppg is not None:
            if player_avg_ppg > 25 and self.star_model:
                archetype_pred = self.star_model.predict(features)[0]
            elif player_avg_ppg < 15 and self.role_model:
                archetype_pred = self.role_model.predict(features)[0]
        
        if archetype_pred is not None:
            predictions.append(archetype_pred)
            weights.append(self.weights['archetype'])
        
        # Weighted average
        if predictions:
            weight_sum = sum(weights)
            final_pred = sum(p * w for p, w in zip(predictions, weights)) / weight_sum
        else:
            final_pred = 15.0  # Fallback
        
        return max(0, final_pred)
    
    def _save_models(self):
        """Save all models to disk"""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        model_package = {
            'xgb_model': self.xgb_model,
            'lgbm_model': self.lgbm_model,
            'star_model': self.star_model,
            'role_model': self.role_model,
            'features': self.features,
            'weights': self.weights,
            'metrics': self.metrics,
            'version': '3.0.0_ensemble',
            'trained_at': datetime.now().isoformat()
        }
        
        filepath = self.models_dir / 'points_ensemble_model.joblib'
        joblib.dump(model_package, filepath)
        logger.info(f"\n✓ Saved ensemble model to {filepath}")
    
    def load_models(self) -> bool:
        """Load ensemble model from disk"""
        filepath = self.models_dir / 'points_ensemble_model.joblib'
        
        if not filepath.exists():
            return False
        
        try:
            package = joblib.load(filepath)
            
            self.xgb_model = package.get('xgb_model')
            self.lgbm_model = package.get('lgbm_model')
            self.star_model = package.get('star_model')
            self.role_model = package.get('role_model')
            self.features = package.get('features', [])
            self.weights = package.get('weights', self.weights)
            self.metrics = package.get('metrics', {})
            
            logger.info(f"Loaded ensemble model (v{package.get('version', 'unknown')})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ensemble: {e}")
            return False
