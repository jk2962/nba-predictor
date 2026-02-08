"""
Advanced feature engineering for points prediction.
Captures shot volume, efficiency, opponent strength, and situational factors.
Target: Reduce MAE from 6.01 to <6.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PointsFeatureEngineer:
    """
    Comprehensive feature engineering for NBA points prediction.
    Creates 55+ features across 7 categories.
    """
    
    def __init__(self):
        self.feature_groups = {
            'shot_volume': [],
            'efficiency': [],
            'situational': [],
            'role': [],
            'historical': [],
            'momentum': [],
            'interaction': []
        }
    
    def create_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create complete feature set for points prediction.
        
        Args:
            df: DataFrame with game logs
        
        Returns:
            DataFrame with all engineered features
        """
        logger.info("Creating advanced features for points prediction...")
        
        # Sort by player and date for rolling calculations
        df = df.sort_values(['player_id', 'game_date']).copy()
        
        # Create feature groups
        df = self._create_shot_volume_features(df)
        df = self._create_efficiency_features(df)
        df = self._create_situational_features(df)
        df = self._create_role_features(df)
        df = self._create_historical_features(df)
        df = self._create_momentum_features(df)
        df = self._create_interaction_features(df)
        
        total = sum(len(f) for f in self.feature_groups.values())
        logger.info(f"Created {total} advanced features")
        
        return df
    
    def _create_shot_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Shot attempt patterns - strong predictor of points"""
        features = []
        
        # Points per minute (efficiency measure)
        if 'minutes' in df.columns:
            df['pts_per_min'] = df['points'] / (df['minutes'] + 0.1)
            
            for window in [3, 5, 10]:
                col = f'pts_per_min_avg_{window}'
                df[col] = df.groupby('player_id')['pts_per_min'].transform(
                    lambda x: x.rolling(window, min_periods=1).mean().shift(1)
                )
                features.append(col)
        
        # Minutes played trends (more minutes = more points opportunity)
        if 'minutes' in df.columns:
            for window in [3, 5, 10]:
                col = f'min_avg_{window}'
                df[col] = df.groupby('player_id')['minutes'].transform(
                    lambda x: x.rolling(window, min_periods=1).mean().shift(1)
                )
                features.append(col)
            
            # Minutes volatility
            df['min_volatility'] = df.groupby('player_id')['minutes'].transform(
                lambda x: x.rolling(5, min_periods=2).std().shift(1)
            )
            features.append('min_volatility')
            
            # Minutes trend (increasing/decreasing role)
            df['min_trend'] = df.groupby('player_id')['minutes'].transform(
                lambda x: x.rolling(3, min_periods=1).mean().shift(1) - 
                         x.rolling(10, min_periods=3).mean().shift(1)
            )
            features.append('min_trend')
        
        self.feature_groups['shot_volume'] = features
        return df
    
    def _create_efficiency_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Shooting efficiency metrics"""
        features = []
        
        # Field goal percentage rolling
        if 'fg_pct' in df.columns:
            for window in [3, 5, 10]:
                col = f'fg_pct_avg_{window}'
                df[col] = df.groupby('player_id')['fg_pct'].transform(
                    lambda x: x.rolling(window, min_periods=1).mean().shift(1)
                )
                features.append(col)
            
            # FG% volatility (consistency)
            df['fg_pct_volatility'] = df.groupby('player_id')['fg_pct'].transform(
                lambda x: x.rolling(10, min_periods=3).std().shift(1)
            )
            features.append('fg_pct_volatility')
        
        # Three-point percentage
        if 'fg3_pct' in df.columns:
            for window in [5, 10]:
                col = f'fg3_pct_avg_{window}'
                df[col] = df.groupby('player_id')['fg3_pct'].transform(
                    lambda x: x.rolling(window, min_periods=1).mean().shift(1)
                )
                features.append(col)
        
        # Free throw percentage
        if 'ft_pct' in df.columns:
            df['ft_pct_avg_10'] = df.groupby('player_id')['ft_pct'].transform(
                lambda x: x.rolling(10, min_periods=1).mean().shift(1)
            )
            features.append('ft_pct_avg_10')
        
        self.feature_groups['efficiency'] = features
        return df
    
    def _create_situational_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Game situation and context"""
        features = []
        
        # Home/away
        if 'is_home' in df.columns:
            features.append('is_home')
            
            # Home scoring differential
            df['home_pts_avg'] = df[df['is_home'] == 1].groupby('player_id')['points'].transform('mean')
            df['away_pts_avg'] = df[df['is_home'] == 0].groupby('player_id')['points'].transform('mean')
            df['home_away_diff'] = df['home_pts_avg'].fillna(0) - df['away_pts_avg'].fillna(0)
            features.append('home_away_diff')
        
        # Rest days
        if 'rest_days' in df.columns:
            features.append('rest_days')
            
            # Back-to-back indicator
            df['back_to_back'] = (df['rest_days'] == 0).astype(int)
            features.append('back_to_back')
            
            # Well rested indicator (3+ days)
            df['well_rested'] = (df['rest_days'] >= 3).astype(int)
            features.append('well_rested')
        
        # Day of week effects (if game_date available)
        if 'game_date' in df.columns:
            df['game_date'] = pd.to_datetime(df['game_date'])
            df['day_of_week'] = df['game_date'].dt.dayofweek
            features.append('day_of_week')
            
            # Month (season progression)
            df['month'] = df['game_date'].dt.month
            features.append('month')
        
        self.feature_groups['situational'] = features
        return df
    
    def _create_role_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Player role and usage features"""
        features = []
        
        # Season averages (baseline expectation)
        df['season_pts_avg'] = df.groupby('player_id')['points'].transform(
            lambda x: x.expanding().mean().shift(1)
        )
        features.append('season_pts_avg')
        
        # Season std
        df['season_pts_std'] = df.groupby('player_id')['points'].transform(
            lambda x: x.expanding().std().shift(1)
        )
        features.append('season_pts_std')
        
        # Scoring consistency (CV)
        df['scoring_cv'] = df['season_pts_std'] / (df['season_pts_avg'] + 0.1)
        features.append('scoring_cv')
        
        # Games played (experience factor)
        df['games_played'] = df.groupby('player_id').cumcount()
        features.append('games_played')
        
        # Position encoding (one-hot would be done at training time)
        if 'position' in df.columns:
            features.append('position')
        
        self.feature_groups['role'] = features
        return df
    
    def _create_historical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Historical points performance - multi-window rolling averages"""
        features = []
        
        # Rolling averages at multiple windows
        for window in [3, 5, 7, 10, 15, 20]:
            col = f'pts_avg_{window}'
            df[col] = df.groupby('player_id')['points'].transform(
                lambda x: x.rolling(window, min_periods=1).mean().shift(1)
            )
            features.append(col)
        
        # Exponential moving average (weights recent games more)
        for span in [3, 5, 10]:
            col = f'pts_ema_{span}'
            df[col] = df.groupby('player_id')['points'].transform(
                lambda x: x.ewm(span=span, min_periods=1).mean().shift(1)
            )
            features.append(col)
        
        # Recent variance
        df['pts_std_10'] = df.groupby('player_id')['points'].transform(
            lambda x: x.rolling(10, min_periods=2).std().shift(1)
        )
        features.append('pts_std_10')
        
        # Recent max/min (ceiling/floor)
        df['pts_max_10'] = df.groupby('player_id')['points'].transform(
            lambda x: x.rolling(10, min_periods=1).max().shift(1)
        )
        features.append('pts_max_10')
        
        df['pts_min_10'] = df.groupby('player_id')['points'].transform(
            lambda x: x.rolling(10, min_periods=1).min().shift(1)
        )
        features.append('pts_min_10')
        
        self.feature_groups['historical'] = features
        return df
    
    def _create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Momentum and trend features"""
        features = []
        
        # Recent vs season (hot/cold)
        df['pts_vs_season'] = df['pts_avg_5'] - df['season_pts_avg']
        features.append('pts_vs_season')
        
        # Short vs medium term momentum
        df['pts_momentum_3v10'] = df['pts_avg_3'] - df['pts_avg_10']
        features.append('pts_momentum_3v10')
        
        # Streak detection (games over 20 in last 5)
        df['games_over_20_last_5'] = df.groupby('player_id')['points'].transform(
            lambda x: x.rolling(5, min_periods=1).apply(
                lambda y: (y > 20).sum()
            ).shift(1)
        )
        features.append('games_over_20_last_5')
        
        # Streak detection (games under 10 in last 5)
        df['games_under_10_last_5'] = df.groupby('player_id')['points'].transform(
            lambda x: x.rolling(5, min_periods=1).apply(
                lambda y: (y < 10).sum()
            ).shift(1)
        )
        features.append('games_under_10_last_5')
        
        # Z-score of last game (how unusual was it)
        df['last_game_zscore'] = df.groupby('player_id')['points'].transform(
            lambda x: (x.shift(1) - x.rolling(20, min_periods=5).mean().shift(1)) / 
                     (x.rolling(20, min_periods=5).std().shift(1) + 0.1)
        )
        features.append('last_game_zscore')
        
        self.feature_groups['momentum'] = features
        return df
    
    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Feature interactions for non-linear relationships"""
        features = []
        
        # Minutes × Efficiency interaction
        if 'min_avg_5' in df.columns and 'fg_pct_avg_5' in df.columns:
            df['min_x_efficiency'] = df['min_avg_5'] * df['fg_pct_avg_5']
            features.append('min_x_efficiency')
        
        # Home × Rest interaction
        if 'is_home' in df.columns and 'rest_days' in df.columns:
            df['home_x_rested'] = df['is_home'] * np.minimum(df['rest_days'], 4)
            features.append('home_x_rested')
        
        # Momentum × Consistency interaction
        if 'pts_momentum_3v10' in df.columns and 'scoring_cv' in df.columns:
            df['momentum_x_consistency'] = df['pts_momentum_3v10'] * (1 - df['scoring_cv'])
            features.append('momentum_x_consistency')
        
        # Recent form × baseline
        if 'pts_avg_5' in df.columns and 'season_pts_avg' in df.columns:
            df['form_x_baseline'] = df['pts_avg_5'] * df['season_pts_avg'] / 100
            features.append('form_x_baseline')
        
        self.feature_groups['interaction'] = features
        return df
    
    def get_feature_list(self, exclude_categorical: bool = False) -> List[str]:
        """Get flattened list of all numeric features"""
        all_features = []
        for group_name, features in self.feature_groups.items():
            all_features.extend(features)
        
        # Remove duplicates
        all_features = list(dict.fromkeys(all_features))
        
        # Optionally exclude categorical
        if exclude_categorical:
            categorical = ['position', 'day_of_week', 'month']
            all_features = [f for f in all_features if f not in categorical]
        
        return all_features
    
    def get_feature_summary(self) -> Dict[str, int]:
        """Get count of features per group"""
        return {name: len(features) for name, features in self.feature_groups.items()}
