"""
NBA Player Performance Prediction - ML Prediction Module
"""
import os
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List, Dict, Any
from datetime import date, datetime
import joblib
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PerformancePredictor:
    """XGBoost-based player performance predictor."""
    
    MODEL_VERSION = "1.0.0"
    
    def __init__(self):
        """Initialize the predictor."""
        self.models: Dict[str, XGBRegressor] = {}
        self.metrics: Dict[str, Dict[str, float]] = {}
        self._models_loaded = False
        
        # Feature columns
        self.feature_columns = [
            # Rolling averages
            'pts_avg_5', 'pts_avg_10', 'pts_avg_15',
            'reb_avg_5', 'reb_avg_10', 'reb_avg_15',
            'ast_avg_5', 'ast_avg_10', 'ast_avg_15',
            'min_avg_5', 'min_avg_10', 'min_avg_15',
            # Game context
            'is_home', 'rest_days',
            # Season averages
            'season_pts_avg', 'season_reb_avg', 'season_ast_avg', 'season_min_avg',
            # Shooting
            'fg_pct_avg_10', 'fg3_pct_avg_10', 'ft_pct_avg_10',
            # Opponent (encoded)
            'opponent_def_rating',
        ]
        
        self.target_columns = ['points', 'rebounds', 'assists']
    
    def _get_model_path(self, target: str) -> str:
        """Get the path to a saved model file."""
        os.makedirs(settings.models_dir, exist_ok=True)
        return os.path.join(settings.models_dir, f"{target}_model.joblib")
    
    def _get_metrics_path(self) -> str:
        """Get the path to saved metrics file."""
        os.makedirs(settings.models_dir, exist_ok=True)
        return os.path.join(settings.models_dir, "metrics.joblib")
    
    def load_models(self) -> bool:
        """
        Load trained models from disk.
        
        Returns:
            True if all models loaded successfully, False otherwise
        """
        if self._models_loaded:
            return True
        
        try:
            for target in self.target_columns:
                model_path = self._get_model_path(target)
                if os.path.exists(model_path):
                    self.models[target] = joblib.load(model_path)
                    logger.info(f"Loaded {target} model from {model_path}")
                else:
                    logger.warning(f"Model file not found: {model_path}")
                    return False
            
            # Load metrics
            metrics_path = self._get_metrics_path()
            if os.path.exists(metrics_path):
                self.metrics = joblib.load(metrics_path)
            
            self._models_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def create_features(self, stats_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create feature matrix from player stats.
        
        Args:
            stats_df: DataFrame with player game stats
            
        Returns:
            DataFrame with engineered features
        """
        df = stats_df.copy()
        
        # Sort by date
        df = df.sort_values('game_date')
        
        # Rolling averages
        for window in [5, 10, 15]:
            for col, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                               ('assists', 'ast'), ('minutes', 'min')]:
                df[f'{prefix}_avg_{window}'] = df[col].rolling(
                    window=window, min_periods=1
                ).mean().shift(1)
        
        # Shooting percentages rolling average
        for col in ['fg_pct', 'fg3_pct', 'ft_pct']:
            df[f'{col}_avg_10'] = df[col].rolling(
                window=10, min_periods=1
            ).mean().shift(1)
        
        # Season averages (expanding mean)
        for col, prefix in [('points', 'pts'), ('rebounds', 'reb'), 
                           ('assists', 'ast'), ('minutes', 'min')]:
            df[f'season_{prefix}_avg'] = df[col].expanding().mean().shift(1)
        
        # Rest days (already in data if available)
        if 'rest_days' not in df.columns:
            df['rest_days'] = 1
        
        # Home/away indicator
        df['is_home'] = df['is_home'].astype(int)
        
        # Opponent defensive rating (placeholder - would need opponent data)
        if 'opponent_def_rating' not in df.columns:
            df['opponent_def_rating'] = 110  # League average
        
        return df
    
    def train(self, stats_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Train models on historical data.
        
        Args:
            stats_df: DataFrame with player game stats
            
        Returns:
            Dictionary of metrics for each model
        """
        logger.info("Starting model training...")
        
        # Create features
        df = self.create_features(stats_df)
        
        # Drop rows with NaN in feature columns
        feature_cols_present = [c for c in self.feature_columns if c in df.columns]
        df = df.dropna(subset=feature_cols_present)
        
        if len(df) < 100:
            logger.warning(f"Insufficient data for training: {len(df)} rows")
            return {}
        
        X = df[feature_cols_present]
        
        metrics = {}
        
        for target in self.target_columns:
            if target not in df.columns:
                continue
                
            y = df[target]
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train XGBoost model
            model = XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                objective='reg:squarederror',
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            metrics[target] = {
                'mae': round(mae, 3),
                'rmse': round(rmse, 3),
                'r2': round(r2, 3),
                'training_samples': len(X_train),
                'last_trained': datetime.utcnow().isoformat()
            }
            
            # Save model
            self.models[target] = model
            joblib.dump(model, self._get_model_path(target))
            
            logger.info(f"Trained {target} model: MAE={mae:.3f}, RMSE={rmse:.3f}, R²={r2:.3f}")
        
        # Save metrics
        self.metrics = metrics
        joblib.dump(metrics, self._get_metrics_path())
        
        self._models_loaded = True
        return metrics
    
    def predict(
        self, 
        player_stats: pd.DataFrame,
        game_date: Optional[date] = None,
        is_home: bool = True,
        rest_days: int = 1,
        opponent_def_rating: float = 110.0
    ) -> Dict[str, Any]:
        """
        Make predictions for a player's next game.
        
        Args:
            player_stats: DataFrame with player's historical stats
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
        
        # Ensure all feature columns exist
        feature_cols_present = [c for c in self.feature_columns if c in latest.columns]
        X = latest[feature_cols_present]
        
        predictions = {}
        
        for target in self.target_columns:
            if target not in self.models:
                continue
            
            model = self.models[target]
            
            # Point prediction
            pred = model.predict(X)[0]
            
            # Estimate confidence interval using prediction variance
            # This is a simplified approach - in production, use quantile regression
            # or conformal prediction for better intervals
            std_estimate = self._estimate_prediction_std(model, X, target)
            
            predictions[target] = {
                'predicted': round(float(pred), 1),
                'lower': round(float(pred - 1.96 * std_estimate), 1),
                'upper': round(float(pred + 1.96 * std_estimate), 1)
            }
        
        return predictions
    
    def _estimate_prediction_std(
        self, 
        model: XGBRegressor, 
        X: pd.DataFrame,
        target: str
    ) -> float:
        """
        Estimate standard deviation of predictions.
        
        This is a simplified approach using historical MAE as a proxy.
        """
        if target in self.metrics:
            # Use MAE as a rough estimate of standard deviation
            return self.metrics[target].get('mae', 3.0) * 1.25
        return 3.0  # Default fallback
    
    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get the model metrics."""
        if not self.metrics:
            metrics_path = self._get_metrics_path()
            if os.path.exists(metrics_path):
                self.metrics = joblib.load(metrics_path)
        return self.metrics


# Global predictor instance
predictor = PerformancePredictor()
