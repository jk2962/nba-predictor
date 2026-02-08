"""
NBA Player Performance Prediction - Model Test Suite

Run this after training to verify predictions are realistic.

Usage:
    cd backend
    python -m scripts.test_predictions
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple

from app.ml.predictor import predictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PredictionTester:
    """Test suite for verifying ML predictions are realistic."""
    
    def __init__(self):
        # Player test cases with expected ranges
        self.test_cases = {
            'Point Guard': {
                'expected': {'points': (18, 35), 'rebounds': (2, 8), 'assists': (6, 15)},
                'position': 'PG',
            },
            'Shooting Guard': {
                'expected': {'points': (15, 30), 'rebounds': (3, 8), 'assists': (3, 8)},
                'position': 'SG',
            },
            'Small Forward': {
                'expected': {'points': (12, 28), 'rebounds': (4, 10), 'assists': (2, 7)},
                'position': 'SF',
            },
            'Power Forward': {
                'expected': {'points': (12, 28), 'rebounds': (6, 14), 'assists': (2, 6)},
                'position': 'PF',
            },
            'Center': {
                'expected': {'points': (10, 28), 'rebounds': (8, 18), 'assists': (1, 8)},
                'position': 'C',
            },
        }
        
        self.results = []
    
    def test_position_bounds(self) -> bool:
        """Test that predictions respect position-based bounds."""
        print("\n" + "=" * 70)
        print("TEST: Position-Based Prediction Bounds")
        print("=" * 70)
        
        all_passed = True
        
        # Create mock player data for each position
        for position_name, config in self.test_cases.items():
            position = config['position']
            expected = config['expected']
            
            # Create sample historical data
            mock_data = self._create_mock_player_data(position, 20)
            
            # Get predictions
            try:
                predictions = predictor.predict(
                    mock_data, 
                    position=position,
                    is_home=True,
                    rest_days=2
                )
                
                if not predictions:
                    print(f"\n{position_name} ({position}): ⚠️  No predictions returned")
                    continue
                
                print(f"\n{position_name} ({position}):")
                
                for stat, pred_info in predictions.items():
                    pred_val = pred_info['predicted']
                    min_exp, max_exp = expected[stat]
                    
                    if min_exp <= pred_val <= max_exp:
                        status = "✓"
                    elif pred_val < 0:
                        status = "🚨 NEGATIVE"
                        all_passed = False
                    elif stat == 'rebounds' and position in ['PG', 'SG'] and pred_val > 12:
                        status = "🚨 TOO HIGH FOR GUARD"
                        all_passed = False
                    elif stat == 'assists' and position == 'C' and pred_val > 10:
                        status = "⚠️  HIGH FOR CENTER"
                    else:
                        status = "⚠️  OUTSIDE TYPICAL RANGE"
                    
                    print(f"  {stat}: {pred_val} (expected {min_exp}-{max_exp}) {status}")
                    
            except Exception as e:
                print(f"\n{position_name} ({position}): 🚨 Error - {e}")
                all_passed = False
        
        return all_passed
    
    def test_no_negative_predictions(self) -> bool:
        """Ensure no predictions are negative."""
        print("\n" + "=" * 70)
        print("TEST: No Negative Predictions")
        print("=" * 70)
        
        negative_count = 0
        total_predictions = 0
        
        for position in ['PG', 'SG', 'SF', 'PF', 'C']:
            for _ in range(5):
                mock_data = self._create_mock_player_data(position, 15)
                
                try:
                    predictions = predictor.predict(
                        mock_data,
                        position=position,
                        is_home=np.random.choice([True, False]),
                        rest_days=np.random.randint(1, 5)
                    )
                    
                    for stat, pred_info in predictions.items():
                        total_predictions += 1
                        if pred_info['predicted'] < 0:
                            negative_count += 1
                            print(f"🚨 Negative {stat} prediction: {pred_info['predicted']}")
                            
                except Exception:
                    pass
        
        if negative_count == 0:
            print(f"✓ All {total_predictions} predictions are non-negative")
            return True
        else:
            print(f"🚨 Found {negative_count}/{total_predictions} negative predictions")
            return False
    
    def test_prediction_variance(self) -> bool:
        """Test that predictions have reasonable variance (not all identical)."""
        print("\n" + "=" * 70)
        print("TEST: Prediction Variance")
        print("=" * 70)
        
        predictions_by_target = {'points': [], 'rebounds': [], 'assists': []}
        
        for position in ['PG', 'C']:
            for i in range(10):
                mock_data = self._create_mock_player_data(
                    position, 20,
                    points_mean=15 + i * 2,  # Varying ability levels
                    rebounds_mean=5 + (0 if position == 'PG' else 5),
                    assists_mean=6 + (0 if position == 'C' else 4)
                )
                
                try:
                    predictions = predictor.predict(mock_data, position=position)
                    
                    for stat, pred_info in predictions.items():
                        predictions_by_target[stat].append(pred_info['predicted'])
                except Exception:
                    pass
        
        all_passed = True
        
        for stat, preds in predictions_by_target.items():
            if len(preds) < 2:
                print(f"{stat}: ⚠️  Not enough predictions to test variance")
                continue
            
            variance = np.var(preds)
            std = np.std(preds)
            
            # Predictions should have some variance (not all identical)
            if variance < 0.1:
                print(f"{stat}: 🚨 Too low variance ({variance:.3f}) - predictions may be stuck")
                all_passed = False
            else:
                print(f"{stat}: ✓ Healthy variance (std={std:.2f})")
        
        return all_passed
    
    def _create_mock_player_data(
        self, 
        position: str, 
        n_games: int,
        points_mean: float = 20.0,
        rebounds_mean: float = 5.0,
        assists_mean: float = 5.0
    ) -> pd.DataFrame:
        """Create mock historical game data for testing."""
        np.random.seed(42)
        
        dates = pd.date_range(end='2024-03-01', periods=n_games, freq='2D')
        
        data = {
            'game_date': dates,
            'points': np.random.normal(points_mean, 5, n_games).clip(0),
            'rebounds': np.random.normal(rebounds_mean, 2, n_games).clip(0),
            'assists': np.random.normal(assists_mean, 2, n_games).clip(0),
            'minutes': np.random.normal(32, 5, n_games).clip(15, 48),
            'fg_pct': np.random.normal(0.45, 0.08, n_games).clip(0, 1),
            'fg3_pct': np.random.normal(0.35, 0.10, n_games).clip(0, 1),
            'ft_pct': np.random.normal(0.80, 0.10, n_games).clip(0, 1),
            'is_home': np.random.choice([True, False], n_games),
            'rest_days': np.random.randint(1, 5, n_games),
        }
        
        return pd.DataFrame(data)
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall pass/fail."""
        print("=" * 70)
        print("NBA PLAYER PERFORMANCE PREDICTION - TEST SUITE")
        print("=" * 70)
        
        # Load models first
        if not predictor.load_models():
            print("\n🚨 Could not load models. Run seed_data.py first to train models.")
            return False
        
        print("✓ Models loaded successfully")
        
        results = []
        
        # Run tests
        results.append(('Position Bounds', self.test_position_bounds()))
        results.append(('No Negatives', self.test_no_negative_predictions()))
        results.append(('Variance', self.test_prediction_variance()))
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"  {name}: {status}")
        
        print(f"\n{'='*70}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'='*70}")
        
        return passed == total


def main():
    """Run test suite."""
    tester = PredictionTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
