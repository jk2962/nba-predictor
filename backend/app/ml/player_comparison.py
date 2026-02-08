"""
Player Comparison Tool - Backend Engine
Compares 2-3 players across predictions, season stats, recent form, and matchups.

Usage:
    from app.ml.player_comparison import PlayerComparator
    
    comparator = PlayerComparator()
    result = comparator.compare_players(['Trae Young', 'Luka Doncic'])
    print(comparator.format_comparison_table(result))
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import joblib
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PlayerComparator:
    """
    Compare multiple NBA players for fantasy basketball decisions.
    
    Features:
    - Next game predictions (points, rebounds, assists)
    - Season averages and trends
    - Recent form (last 5, 10 games)
    - Head-to-head category winners
    - Fantasy point projections
    """
    
    def __init__(self, models_dir: str = 'models', data_path: str = 'data/full_nba_game_logs.csv'):
        self.models_dir = Path(models_dir)
        self.data_path = data_path
        
        # Load models
        self.models = self._load_models()
        
        # Load player data
        self.player_data = self._load_player_data()
        
        # Fantasy scoring weights
        self.scoring_weights = {
            'points': 1.0,
            'rebounds': 1.2,
            'assists': 1.5,
            'steals': 3.0,
            'blocks': 3.0,
        }
    
    def _load_models(self) -> Dict:
        """Load all prediction models"""
        models = {}
        
        for stat in ['points', 'rebounds', 'assists']:
            model_path = self.models_dir / f'{stat}_model.joblib'
            
            if not model_path.exists():
                logger.warning(f"{stat} model not found")
                continue
            
            try:
                loaded = joblib.load(model_path)
                
                if isinstance(loaded, dict):
                    models[stat] = {
                        'model': loaded['model'],
                        'features': loaded.get('features', []),
                        'mae': loaded.get('mae', None)
                    }
                else:
                    models[stat] = {'model': loaded, 'features': [], 'mae': None}
                
                logger.info(f"Loaded {stat} model")
                
            except Exception as e:
                logger.error(f"Failed to load {stat} model: {e}")
        
        return models
    
    def _load_player_data(self) -> pd.DataFrame:
        """Load and prepare player game log data"""
        try:
            df = pd.read_csv(self.data_path)
            df['game_date'] = pd.to_datetime(df['game_date'])
            df = df.sort_values(['player_id', 'game_date'])
            
            logger.info(f"Loaded {df['player_id'].nunique()} players, {len(df)} games")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load player data: {e}")
            return pd.DataFrame()
    
    def get_player_latest_features(self, player_name: str) -> Optional[pd.Series]:
        """Get most recent feature vector for a player"""
        
        player_games = self.player_data[
            self.player_data['player_name'].str.lower() == player_name.lower()
        ]
        
        if len(player_games) == 0:
            return None
        
        return player_games.iloc[-1]
    
    def predict_player_stats(self, player_features: pd.Series) -> Dict:
        """Predict stats for a player's next game"""
        
        predictions = {}
        
        for stat in ['points', 'rebounds', 'assists']:
            if stat not in self.models:
                predictions[stat] = {'prediction': None, 'error': f'{stat} model unavailable'}
                continue
            
            model_info = self.models[stat]
            model = model_info['model']
            features = model_info['features']
            mae = model_info['mae']
            
            missing = [f for f in features if f not in player_features.index]
            
            if missing:
                predictions[stat] = {'prediction': None, 'error': f'Missing features'}
                continue
            
            try:
                X = player_features[features].values.reshape(1, -1)
                pred = max(0, model.predict(X)[0])
                
                result = {'prediction': round(pred, 1)}
                
                # 80% confidence interval
                if mae:
                    margin = 1.28 * mae
                    result['confidence_80'] = {
                        'lower': round(max(0, pred - margin), 1),
                        'upper': round(pred + margin, 1)
                    }
                
                predictions[stat] = result
                
            except Exception as e:
                predictions[stat] = {'prediction': None, 'error': str(e)}
        
        return predictions
    
    def get_player_stats_summary(self, player_name: str) -> Dict:
        """Get comprehensive stats summary for a player"""
        
        player_games = self.player_data[
            self.player_data['player_name'].str.lower() == player_name.lower()
        ]
        
        if len(player_games) == 0:
            return {'error': f'Player {player_name} not found'}
        
        summary = {
            'player_name': player_games['player_name'].iloc[0],
            'games_played': len(player_games)
        }
        
        # Season averages
        summary['season_avg'] = {
            'points': round(player_games['points'].mean(), 1),
            'rebounds': round(player_games['rebounds'].mean(), 1),
            'assists': round(player_games['assists'].mean(), 1),
        }
        
        # Last 5 games
        last_5 = player_games.tail(5)
        summary['last_5_avg'] = {
            'points': round(last_5['points'].mean(), 1),
            'rebounds': round(last_5['rebounds'].mean(), 1),
            'assists': round(last_5['assists'].mean(), 1),
        }
        
        # Trend (last 5 vs previous 5)
        if len(player_games) >= 10:
            prev_5 = player_games.tail(10).head(5)
            
            summary['trend'] = {
                'points': 'up' if last_5['points'].mean() > prev_5['points'].mean() else 'down',
                'rebounds': 'up' if last_5['rebounds'].mean() > prev_5['rebounds'].mean() else 'down',
                'assists': 'up' if last_5['assists'].mean() > prev_5['assists'].mean() else 'down',
            }
        else:
            summary['trend'] = None
        
        # Season highs
        summary['season_high'] = {
            'points': int(player_games['points'].max()),
            'rebounds': int(player_games['rebounds'].max()),
            'assists': int(player_games['assists'].max()),
        }
        
        return summary
    
    def get_matchup_context(self, player_features: pd.Series) -> Dict:
        """Get context about upcoming matchup"""
        
        context = {}
        
        if 'opponent' in player_features.index and pd.notna(player_features['opponent']):
            context['opponent'] = player_features['opponent']
        
        if 'is_home' in player_features.index:
            context['location'] = 'Home' if player_features['is_home'] == 1 else 'Away'
        
        if 'rest_days' in player_features.index:
            days = player_features['rest_days']
            if days == 0:
                context['rest'] = 'Back-to-back'
            elif days >= 3:
                context['rest'] = 'Well rested'
            else:
                context['rest'] = f'{int(days)} day(s) rest'
        
        return context
    
    def compare_players(self, player_names: List[str]) -> Dict:
        """
        Main comparison function - compare multiple players.
        
        Args:
            player_names: List of 2-3 player names
        
        Returns:
            Comprehensive comparison dictionary
        """
        
        if len(player_names) < 2:
            return {'error': 'Need at least 2 players'}
        
        if len(player_names) > 3:
            return {'error': 'Maximum 3 players'}
        
        comparison = {
            'players': {},
            'head_to_head': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Gather data for each player
        for player_name in player_names:
            player_data = {}
            
            features = self.get_player_latest_features(player_name)
            
            if features is None:
                player_data['error'] = f'Player not found'
                comparison['players'][player_name] = player_data
                continue
            
            player_data['name'] = features.get('player_name', player_name)
            
            # Predictions
            predictions = self.predict_player_stats(features)
            player_data['predictions'] = predictions
            
            # Stats summary
            stats = self.get_player_stats_summary(player_name)
            if 'error' not in stats:
                player_data['season_avg'] = stats['season_avg']
                player_data['last_5_avg'] = stats['last_5_avg']
                player_data['trend'] = stats['trend']
                player_data['season_high'] = stats['season_high']
            
            # Matchup
            matchup = self.get_matchup_context(features)
            player_data['matchup'] = matchup
            
            comparison['players'][player_name] = player_data
        
        # Head-to-head
        comparison['head_to_head'] = self._calculate_head_to_head(
            comparison['players'], 
            player_names
        )
        
        return comparison
    
    def _calculate_head_to_head(self, players_data: Dict, player_names: List[str]) -> Dict:
        """Calculate head-to-head winners"""
        
        h2h = {
            'predictions': {},
            'season_avg': {},
            'fantasy_points': {}
        }
        
        # Predictions head-to-head
        for stat in ['points', 'rebounds', 'assists']:
            stat_values = {}
            
            for player in player_names:
                if player not in players_data or 'error' in players_data[player]:
                    continue
                
                if 'predictions' in players_data[player]:
                    pred = players_data[player]['predictions'].get(stat, {})
                    if 'prediction' in pred and pred['prediction'] is not None:
                        stat_values[player] = pred['prediction']
            
            if stat_values:
                winner = max(stat_values, key=stat_values.get)
                h2h['predictions'][stat] = {
                    'winner': winner,
                    'values': stat_values
                }
        
        # Season averages
        for stat in ['points', 'rebounds', 'assists']:
            stat_values = {}
            
            for player in player_names:
                if player not in players_data or 'error' in players_data[player]:
                    continue
                
                if 'season_avg' in players_data[player]:
                    stat_values[player] = players_data[player]['season_avg'][stat]
            
            if stat_values:
                winner = max(stat_values, key=stat_values.get)
                h2h['season_avg'][stat] = {'winner': winner, 'values': stat_values}
        
        # Fantasy points
        fantasy_scores = {}
        
        for player in player_names:
            if player not in players_data or 'error' in players_data[player]:
                continue
            
            if 'predictions' in players_data[player]:
                score = 0
                preds = players_data[player]['predictions']
                
                for stat, weight in self.scoring_weights.items():
                    if stat in preds and 'prediction' in preds[stat]:
                        pred_val = preds[stat]['prediction']
                        if pred_val is not None:
                            score += pred_val * weight
                
                fantasy_scores[player] = round(score, 1)
        
        if fantasy_scores:
            winner = max(fantasy_scores, key=fantasy_scores.get)
            h2h['fantasy_points'] = {'winner': winner, 'scores': fantasy_scores}
        
        return h2h
    
    def format_comparison_table(self, comparison: Dict) -> str:
        """Format comparison results as readable text table"""
        
        if 'error' in comparison:
            return f"Error: {comparison['error']}"
        
        player_names = list(comparison['players'].keys())
        
        lines = []
        lines.append("=" * 90)
        lines.append(" " * 30 + "PLAYER COMPARISON")
        lines.append("=" * 90)
        lines.append("")
        
        # Headers
        header = f"{'Category':<20}"
        for player in player_names:
            header += f"{player[:22]:^23}"
        lines.append(header)
        lines.append("-" * 90)
        
        # Matchup info
        row = f"{'Opponent':<20}"
        for player in player_names:
            opp = comparison['players'][player].get('matchup', {}).get('opponent', 'N/A')
            row += f"{opp:^23}"
        lines.append(row)
        
        row = f"{'Location':<20}"
        for player in player_names:
            loc = comparison['players'][player].get('matchup', {}).get('location', 'N/A')
            row += f"{loc:^23}"
        lines.append(row)
        
        lines.append("")
        lines.append("-" * 90)
        lines.append(" " * 30 + "NEXT GAME PREDICTIONS")
        lines.append("-" * 90)
        
        # Predictions
        for stat in ['points', 'rebounds', 'assists']:
            h2h = comparison['head_to_head'].get('predictions', {}).get(stat, {})
            winner = h2h.get('winner')
            
            row = f"{stat.capitalize():<20}"
            
            for player in player_names:
                pred_data = comparison['players'][player].get('predictions', {}).get(stat, {})
                
                if 'prediction' in pred_data and pred_data['prediction'] is not None:
                    pred = pred_data['prediction']
                    conf = pred_data.get('confidence_80', {})
                    
                    marker = " ★" if player == winner else ""
                    
                    if conf:
                        display = f"{pred:.1f}({conf['lower']:.0f}-{conf['upper']:.0f}){marker}"
                    else:
                        display = f"{pred:.1f}{marker}"
                    
                    row += f"{display:^23}"
                else:
                    row += f"{'N/A':^23}"
            
            lines.append(row)
        
        # Fantasy total
        fantasy = comparison['head_to_head'].get('fantasy_points', {})
        if fantasy:
            winner = fantasy.get('winner')
            row = f"{'Fantasy Points':<20}"
            
            for player in player_names:
                score = fantasy['scores'].get(player)
                if score is not None:
                    marker = " ★" if player == winner else ""
                    row += f"{score:.1f}{marker}:^23"
                else:
                    row += f"{'N/A':^23}"
            
            lines.append(row)
        
        lines.append("")
        lines.append("-" * 90)
        lines.append(" " * 30 + "SEASON AVERAGES")
        lines.append("-" * 90)
        
        # Season averages
        for stat in ['points', 'rebounds', 'assists']:
            h2h = comparison['head_to_head'].get('season_avg', {}).get(stat, {})
            winner = h2h.get('winner')
            
            row = f"{stat.capitalize():<20}"
            
            for player in player_names:
                avg = comparison['players'][player].get('season_avg', {}).get(stat)
                
                if avg is not None:
                    marker = " ★" if player == winner else ""
                    row += f"{avg:.1f}{marker}:^23"
                else:
                    row += f"{'N/A':^23}"
            
            lines.append(row)
        
        lines.append("")
        lines.append("-" * 90)
        lines.append(" " * 30 + "RECENT FORM (Last 5)")
        lines.append("-" * 90)
        
        # Recent form
        for stat in ['points', 'rebounds', 'assists']:
            row = f"{stat.capitalize():<20}"
            
            for player in player_names:
                avg = comparison['players'][player].get('last_5_avg', {}).get(stat)
                trend = comparison['players'][player].get('trend', {})
                
                if avg is not None:
                    arrow = " ↑" if trend and trend.get(stat) == 'up' else " ↓" if trend else ""
                    row += f"{avg:.1f}{arrow}:^23"
                else:
                    row += f"{'N/A':^23}"
            
            lines.append(row)
        
        lines.append("")
        lines.append("=" * 90)
        lines.append("★ = Winner  |  ↑ = Trending up  |  ↓ = Trending down")
        lines.append("=" * 90)
        
        return "\n".join(lines)


# Testing
if __name__ == "__main__":
    print("="*90)
    print(" " * 30 + "PLAYER COMPARISON TOOL TEST")
    print("="*90)
    
    comparator = PlayerComparator()
    
    # Test 1
    print("\n\nTEST 1: Trae Young vs Luka Doncic")
    print("-" * 90)
    
    comparison = comparator.compare_players(['Trae Young', 'Luka Doncic'])
    print(comparator.format_comparison_table(comparison))
    
    # Test 2
    print("\n\nTEST 2: Three-Player Comparison")
    print("-" * 90)
    
    comparison = comparator.compare_players(['Stephen Curry', 'Damian Lillard', 'Kyrie Irving'])
    print(comparator.format_comparison_table(comparison))
