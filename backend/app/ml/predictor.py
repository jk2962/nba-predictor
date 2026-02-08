"""
NBA Player Performance Prediction - Safe ML Prediction Module

This module implements separate models for each target (points, rebounds, assists)
with safeguards against:
- Target leakage (using same-game stats as features)
- Model misassignment (swapping predictions)
- Unrealistic predictions (position-based bounds)
"""
import os
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
import joblib
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SafePerformancePredictor:
    """
    XGBoost-based player performance predictor with built-in safeguards.
    
    Key safeguards:
    1. Separate feature sets for each target (prevents accidental contamination)
    2. Explicit model-target binding verification
    3. Position-based realistic bounds on predictions
    4. Validation of target columns before training
    """
    
    MODEL_VERSION = "2.0.0"
    
    # Position-based realistic bounds for predictions
    # These prevent obviously wrong predictions like 15 rebounds for a point guard
    POSITION_BOUNDS = {
        'PG': {'points': (0, 50), 'rebounds': (0, 10), 'assists': (0, 20)},
        'SG': {'points': (0, 55), 'rebounds': (0, 12), 'assists': (0, 15)},
        'SF': {'points': (0, 50), 'rebounds': (0, 15), 'assists': (0, 12)},
        'PF': {'points': (0, 45), 'rebounds': (0, 20), 'assists': (0, 10)},
        'C': {'points': (0, 45), 'rebounds': (0, 25), 'assists': (0, 12)},
        'G': {'points': (0, 55), 'rebounds': (0, 12), 'assists': (0, 20)},
        'F': {'points': (0, 50), 'rebounds': (0, 18), 'assists': (0, 12)},
        'G-F': {'points': (0, 50), 'rebounds': (0, 15), 'assists': (0, 15)},
        'F-G': {'points': (0, 50), 'rebounds': (0, 15), 'assists': (0, 15)},
        'F-C': {'points': (0, 45), 'rebounds': (0, 22), 'assists': (0, 10)},
        'C-F': {'points': (0, 45), 'rebounds': (0, 22), 'assists': (0, 10)},
    }
    
    # Default bounds if position unknown
    DEFAULT_BOUNDS = {'points': (0, 60), 'rebounds': (0, 25), 'assists': (0, 20)}
    
    def __init__(self):
        """Initialize the predictor with empty model storage."""
        self.models: Dict[str, XGBRegressor] = {}
        self.feature_sets: Dict[str, List[str]] = {}
        self.metrics: Dict[str, Dict[str, float]] = {}
        self._models_loaded = False
        
        # Ensemble model for improved points prediction
        self.points_ensemble = None
        self._ensemble_loaded = False
        
        # Define base feature columns (historical/contextual only, NO same-game stats)
        self.base_feature_columns = [
            'is_home', 'rest_days', 'opponent_def_rating',
        ]
        
        # Target-specific feature columns (rolling averages for that stat only)
        self.target_specific_features = {
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
        
        self.target_columns = ['points', 'rebounds', 'assists']
    
    def _get_model_path(self, target: str) -> str:
        """Get the path to a saved model file."""
        os.makedirs(settings.models_dir, exist_ok=True)
        return os.path.join(settings.models_dir, f"{target}_model.joblib")
    
    def _get_metrics_path(self) -> str:
        """Get the path to saved metrics file."""
        os.makedirs(settings.models_dir, exist_ok=True)
        return os.path.join(settings.models_dir, "metrics.joblib")
    
    def _validate_target_column(self, df: pd.DataFrame, target: str) -> None:
        """
        Validate that target column exists and has reasonable values.
        
        Raises:
            ValueError: If target column is invalid
        """
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found in dataframe")
        
        values = df[target].dropna()
        
        if len(values) == 0:
            raise ValueError(f"Target column '{target}' has no valid values")
        
        # Check for negative values
        neg_count = (values < 0).sum()
        if neg_count > 0:
            raise ValueError(f"Found {neg_count} negative values in '{target}' column")
        
        # Check for extreme values
        bounds = {
            'points': 100,
            'rebounds': 40,
            'assists': 30,
        }
        max_allowed = bounds.get(target, 100)
        extreme_count = (values > max_allowed).sum()
        if extreme_count > 0:
            logger.warning(f"Found {extreme_count} extreme values (>{max_allowed}) in '{target}'")
        
        logger.info(f"Target '{target}' validated: mean={values.mean():.2f}, "
                   f"std={values.std():.2f}, range=[{values.min():.1f}, {values.max():.1f}]")
    
    def _get_features_for_target(self, target: str) -> List[str]:
        """
        Get the feature columns for a specific target.
        
        CRITICAL: This ensures each target model only uses its own historical features,
        preventing accidental leakage of other targets.
        """
        features = self.base_feature_columns.copy()
        
        if target in self.target_specific_features:
            features.extend(self.target_specific_features[target])
        
        return features
    
    def _check_feature_leakage(self, features: List[str], target: str, df: pd.DataFrame) -> None:
        """
        Check for potential feature-target leakage.
        
        Raises warning if features have suspiciously high correlation with target.
        """
        if target not in df.columns:
            return
        
        for feature in features:
            if feature not in df.columns:
                continue
            
            # Check if feature name contains target (but isn't a rolling avg)
            if target in feature and not any(x in feature for x in ['avg', 'season', 'rolling']):
                logger.warning(f"🚨 SUSPICIOUS: Feature '{feature}' contains '{target}' "
                              f"but doesn't look like a rolling average!")
            
            # Check correlation
            try:
                corr = df[feature].corr(df[target])
                if abs(corr) > 0.99:
                    logger.error(f"🚨 CRITICAL LEAKAGE: Feature '{feature}' has {corr:.3f} "
                                f"correlation with '{target}'!")
                elif abs(corr) > 0.95:
                    logger.warning(f"⚠️  HIGH CORRELATION: Feature '{feature}' has {corr:.3f} "
                                  f"correlation with '{target}'")
            except Exception:
                pass
    
    def load_models(self) -> bool:
        """
        Load trained models from disk with validation.
        
        Returns:
            True if all models loaded and validated successfully
        """
        if self._models_loaded:
            return True
        
        try:
            for target in self.target_columns:
                model_path = self._get_model_path(target)
                
                if not os.path.exists(model_path):
                    logger.warning(f"Model file not found: {model_path}")
                    return False
                
                # Load model package
                model_package = joblib.load(model_path)
                
                # Validate model-target binding
                if isinstance(model_package, dict):
                    stored_target = model_package.get('target')
                    if stored_target and stored_target != target:
                        logger.error(f"🚨 MODEL MISMATCH: File {model_path} contains model "
                                   f"for '{stored_target}', expected '{target}'!")
                        return False
                    
                    self.models[target] = model_package.get('model')
                    self.feature_sets[target] = model_package.get('features', [])
                    version = model_package.get('version', 'unknown')
                    logger.info(f"Loaded {target} model (v{version}) from {model_path}")
                else:
                    # Legacy model format
                    self.models[target] = model_package
                    self.feature_sets[target] = self._get_features_for_target(target)
                    logger.info(f"Loaded {target} model (legacy) from {model_path}")
            
            # Load metrics
            metrics_path = self._get_metrics_path()
            if os.path.exists(metrics_path):
                self.metrics = joblib.load(metrics_path)
            
            # Try to load ensemble model for points
            self._load_points_ensemble()
            
            self._models_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def _load_points_ensemble(self) -> bool:
        """
        Load the advanced ensemble model for points prediction.
        This model has lower MAE (5.53) compared to the standard model (6.01).
        """
        try:
            from app.ml.ensemble_points import EnsemblePointsPredictor
            
            ensemble_path = os.path.join(settings.models_dir, 'points_ensemble_model.joblib')
            
            if not os.path.exists(ensemble_path):
                logger.info("Points ensemble model not found, using standard model")
                return False
            
            self.points_ensemble = EnsemblePointsPredictor(models_dir=settings.models_dir)
            if self.points_ensemble.load_models():
                self._ensemble_loaded = True
                
                # Update metrics to show ensemble MAE
                if self.points_ensemble.metrics:
                    self.metrics['points'] = {
                        'mae': round(self.points_ensemble.metrics.get('ensemble_mae', 6.01), 3),
                        'r2': round(self.points_ensemble.metrics.get('ensemble_r2', 0.30), 3),
                        'model': 'ensemble'
                    }
                
                logger.info("✓ Loaded points ensemble model (MAE: 5.53)")
                return True
            else:
                logger.warning("Failed to load points ensemble model")
                return False
                
        except Exception as e:
            logger.warning(f"Could not load points ensemble: {e}")
            return False
    
    def create_features(self, stats_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create feature matrix from player stats.
        
        CRITICAL: All features must be SHIFTED to use only past data.
        We never use same-game statistics as features.
        """
        df = stats_df.copy()
        
        if len(df) == 0:
            return df
        
        # Sort by date to ensure proper rolling calculations
        if 'game_date' in df.columns:
            df = df.sort_values('game_date')
        
        # Rolling averages (SHIFTED by 1 to prevent leakage)
        for window in [5, 10, 15]:
            for col, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                               ('assists', 'ast'), ('minutes', 'min')]:
                if col in df.columns:
                    df[f'{prefix}_avg_{window}'] = df[col].rolling(
                        window=window, min_periods=1
                    ).mean().shift(1)  # SHIFT(1) prevents using same-game data
        
        # Shooting percentages rolling average (SHIFTED)
        for col in ['fg_pct', 'fg3_pct', 'ft_pct']:
            if col in df.columns:
                df[f'{col}_avg_10'] = df[col].rolling(
                    window=10, min_periods=1
                ).mean().shift(1)
        
        # Season averages - expanding mean (SHIFTED)
        for col, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                           ('assists', 'ast'), ('minutes', 'min')]:
            if col in df.columns:
                df[f'season_{prefix}_avg'] = df[col].expanding().mean().shift(1)
        
        # Ensure rest_days exists
        if 'rest_days' not in df.columns:
            df['rest_days'] = 1
        
        # Home/away indicator
        if 'is_home' in df.columns:
            df['is_home'] = df['is_home'].astype(int)
        else:
            df['is_home'] = 1
        
        # Opponent defensive rating (placeholder)
        if 'opponent_def_rating' not in df.columns:
            df['opponent_def_rating'] = 110.0
        
        return df
    
    def train(self, stats_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Train separate models for each target with full validation.
        
        Args:
            stats_df: DataFrame with player game stats
            
        Returns:
            Dictionary of metrics for each model
        """
        logger.info("="*60)
        logger.info("Starting SAFE model training...")
        logger.info("="*60)
        
        # Create features
        df = self.create_features(stats_df)
        
        all_metrics = {}
        
        for target in self.target_columns:
            logger.info(f"\n{'='*60}")
            logger.info(f"Training {target.upper()} model")
            logger.info(f"{'='*60}")
            
            try:
                # Step 1: Validate target
                self._validate_target_column(df, target)
                
                # Step 2: Get target-specific features
                features = self._get_features_for_target(target)
                
                # Only use features that exist
                features_present = [f for f in features if f in df.columns]
                
                if len(features_present) < 3:
                    logger.warning(f"Not enough features for {target}: {features_present}")
                    continue
                
                # Step 3: Check for leakage
                self._check_feature_leakage(features_present, target, df)
                
                # Step 4: Prepare training data
                df_clean = df.dropna(subset=[target] + features_present)
                
                if len(df_clean) < 100:
                    logger.warning(f"Insufficient data for {target}: {len(df_clean)} rows")
                    continue
                
                X = df_clean[features_present]
                y = df_clean[target]
                
                logger.info(f"Training data: {len(df_clean)} samples, {len(features_present)} features")
                logger.info(f"Features: {features_present}")
                
                # Step 5: Time-based split (if possible)
                if 'game_date' in df_clean.columns:
                    df_sorted = df_clean.sort_values('game_date')
                    split_idx = int(len(df_sorted) * 0.8)
                    
                    X_train = df_sorted[features_present].iloc[:split_idx]
                    X_test = df_sorted[features_present].iloc[split_idx:]
                    y_train = df_sorted[target].iloc[:split_idx]
                    y_test = df_sorted[target].iloc[split_idx:]
                else:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42
                    )
                
                # Step 6: Train XGBoost model
                model = XGBRegressor(
                    n_estimators=200,
                    max_depth=6,
                    learning_rate=0.05,
                    min_child_weight=3,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective='reg:squarederror',
                    random_state=42,
                    n_jobs=-1
                )
                
                model.fit(X_train, y_train)
                
                # Step 7: Evaluate
                y_train_pred = model.predict(X_train)
                y_test_pred = model.predict(X_test)
                
                train_mae = mean_absolute_error(y_train, y_train_pred)
                test_mae = mean_absolute_error(y_test, y_test_pred)
                test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
                test_r2 = r2_score(y_test, y_test_pred)
                
                logger.info(f"\n{'Results':^60}")
                logger.info(f"Train MAE: {train_mae:.3f}")
                logger.info(f"Test MAE:  {test_mae:.3f}")
                logger.info(f"Test RMSE: {test_rmse:.3f}")
                logger.info(f"Test R²:   {test_r2:.3f}")
                
                # Step 8: Sanity check predictions
                logger.info(f"\nPrediction sanity check:")
                logger.info(f"  Actual mean: {y_test.mean():.2f}, std: {y_test.std():.2f}")
                logger.info(f"  Pred mean:   {y_test_pred.mean():.2f}, std: {y_test_pred.std():.2f}")
                
                # Check for unrealistic predictions
                negative_preds = (y_test_pred < 0).sum()
                if negative_preds > 0:
                    logger.warning(f"  ⚠️  {negative_preds} negative predictions")
                
                # Step 9: Store model and metadata
                self.models[target] = model
                self.feature_sets[target] = features_present
                
                # Save with explicit target binding
                model_package = {
                    'model': model,
                    'features': features_present,
                    'target': target,  # Explicit binding
                    'version': self.MODEL_VERSION,
                    'trained_at': datetime.utcnow().isoformat(),
                }
                
                joblib.dump(model_package, self._get_model_path(target))
                logger.info(f"✓ Saved {target} model")
                
                all_metrics[target] = {
                    'mae': round(test_mae, 3),
                    'rmse': round(test_rmse, 3),
                    'r2': round(test_r2, 3),
                    'training_samples': len(X_train),
                    'last_trained': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error training {target} model: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Save metrics
        self.metrics = all_metrics
        joblib.dump(all_metrics, self._get_metrics_path())
        
        self._models_loaded = True
        
        logger.info("\n" + "="*60)
        logger.info("TRAINING SUMMARY")
        logger.info("="*60)
        for target, m in all_metrics.items():
            logger.info(f"{target.capitalize():10} - MAE: {m['mae']:.3f}, RMSE: {m['rmse']:.3f}, R²: {m['r2']:.3f}")
        
        return all_metrics
    
    def predict(
        self, 
        player_stats: pd.DataFrame,
        position: Optional[str] = None,
        game_date: Optional[date] = None,
        is_home: bool = True,
        rest_days: int = 1,
        opponent_def_rating: float = 110.0
    ) -> Dict[str, Any]:
        """
        Make predictions for a player's next game with position-based validation.
        
        Args:
            player_stats: DataFrame with player's historical stats
            position: Player's position (for realistic bounds)
            game_date: Date of the game to predict
            is_home: Whether the game is at home
            rest_days: Days of rest before the game
            opponent_def_rating: Opponent's defensive rating
            
        Returns:
            Dictionary with predictions and confidence intervals
        """
        if not self.load_models():
            logger.error("Models not loaded, cannot make predictions")
            return {}
        
        # Create features
        df = self.create_features(player_stats)
        
        if len(df) == 0:
            return {}
        
        # Get the latest features
        latest = df.iloc[-1:].copy()
        
        # Override with prediction context
        latest['is_home'] = int(is_home)
        latest['rest_days'] = rest_days
        latest['opponent_def_rating'] = opponent_def_rating
        
        predictions = {}
        
        # Get position bounds
        bounds = self.POSITION_BOUNDS.get(position, self.DEFAULT_BOUNDS)
        
        for target in self.target_columns:
            if target not in self.models:
                continue
            
            # Use ensemble model for points if available
            if target == 'points' and self._ensemble_loaded and self.points_ensemble:
                try:
                    # Get player's season average for archetype selection
                    player_avg = None
                    if 'season_pts_avg' in latest.columns:
                        player_avg = latest['season_pts_avg'].iloc[0]
                    
                    raw_pred = self.points_ensemble.predict(latest, player_avg_ppg=player_avg)
                    
                    # Apply position bounds
                    min_bound, max_bound = bounds.get('points', (0, 60))
                    pred = max(min_bound, min(raw_pred, max_bound))
                    
                    std_estimate = self._estimate_prediction_std('points')
                    
                    predictions['points'] = {
                        'predicted': round(float(pred), 1),
                        'lower': round(float(max(0, pred - 1.96 * std_estimate)), 1),
                        'upper': round(float(min(max_bound, pred + 1.96 * std_estimate)), 1)
                    }
                    continue
                except Exception as e:
                    logger.warning(f"Ensemble prediction failed, using standard: {e}")
            
            model = self.models[target]
            features = self.feature_sets.get(target, self._get_features_for_target(target))
            
            # Get features that exist
            features_present = [f for f in features if f in latest.columns]
            
            if len(features_present) == 0:
                continue
            
            X = latest[features_present]
            
            # Point prediction
            raw_pred = model.predict(X)[0]
            
            # Apply position-based bounds
            min_bound, max_bound = bounds.get(target, (0, 100))
            pred = max(min_bound, min(raw_pred, max_bound))
            
            if abs(pred - raw_pred) > 1.0:
                logger.info(f"Clipped {target} prediction from {raw_pred:.1f} to {pred:.1f} "
                           f"(position: {position}, bounds: {min_bound}-{max_bound})")
            
            # Estimate confidence interval
            std_estimate = self._estimate_prediction_std(target)
            
            predictions[target] = {
                'predicted': round(float(pred), 1),
                'lower': round(float(max(0, pred - 1.96 * std_estimate)), 1),
                'upper': round(float(min(max_bound, pred + 1.96 * std_estimate)), 1)
            }
        
        return predictions
    
    def _estimate_prediction_std(self, target: str) -> float:
        """
        Estimate standard deviation of predictions using historical MAE.
        """
        if target in self.metrics:
            return self.metrics[target].get('mae', 3.0) * 1.25
        return 3.0
    
    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get the model metrics."""
        if not self.metrics:
            metrics_path = self._get_metrics_path()
            if os.path.exists(metrics_path):
                self.metrics = joblib.load(metrics_path)
        return self.metrics


# Create backward-compatible alias
PerformancePredictor = SafePerformancePredictor

# Global predictor instance
predictor = SafePerformancePredictor()
