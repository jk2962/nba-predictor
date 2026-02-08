"""
NBA Player Performance Prediction - Model Diagnostic Script

Run this script to diagnose issues with trained models.

Usage:
    cd backend
    python -m scripts.diagnose_models
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
import logging
from typing import Optional, Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelDiagnostic:
    """Comprehensive diagnostic tool for ML models."""
    
    def __init__(self, models_dir: str = 'models'):
        self.models_dir = Path(models_dir)
        self.targets = ['points', 'rebounds', 'assists']
        
        # Position-based expected ranges
        self.position_ranges = {
            'PG': {'points': (15, 28), 'rebounds': (2, 6), 'assists': (5, 12)},
            'SG': {'points': (15, 28), 'rebounds': (3, 7), 'assists': (3, 8)},
            'SF': {'points': (12, 25), 'rebounds': (4, 10), 'assists': (2, 6)},
            'PF': {'points': (12, 22), 'rebounds': (6, 12), 'assists': (2, 5)},
            'C': {'points': (10, 25), 'rebounds': (8, 14), 'assists': (1, 5)},
        }
        
        # Known player benchmarks for sanity checks
        self.player_benchmarks = {
            'Trae Young': {'position': 'PG', 'points': (24, 30), 'rebounds': (2, 5), 'assists': (9, 13)},
            'Nikola Jokic': {'position': 'C', 'points': (24, 30), 'rebounds': (10, 14), 'assists': (8, 12)},
            'Rudy Gobert': {'position': 'C', 'points': (10, 16), 'rebounds': (11, 16), 'assists': (0, 3)},
            'Stephen Curry': {'position': 'PG', 'points': (26, 32), 'rebounds': (4, 7), 'assists': (5, 8)},
            'Giannis Antetokounmpo': {'position': 'PF', 'points': (28, 34), 'rebounds': (10, 14), 'assists': (5, 8)},
        }
    
    def run_full_diagnostic(self) -> Dict[str, any]:
        """Run all diagnostic checks and return results."""
        print("=" * 70)
        print("NBA PLAYER PERFORMANCE PREDICTION - MODEL DIAGNOSTIC")
        print("=" * 70)
        
        results = {
            'models_found': {},
            'feature_analysis': {},
            'prediction_tests': {},
            'issues_found': [],
        }
        
        # Check 1: Model files
        print("\n" + "=" * 70)
        print("CHECK 1: MODEL FILES")
        print("=" * 70)
        
        for target in self.targets:
            filepath = self.models_dir / f'{target}_model.joblib'
            
            if filepath.exists():
                print(f"✓ Found {target} model: {filepath}")
                results['models_found'][target] = True
                
                # Load and inspect
                try:
                    model_package = joblib.load(filepath)
                    
                    if isinstance(model_package, dict):
                        # New format with metadata
                        stored_target = model_package.get('target', 'unknown')
                        version = model_package.get('version', 'unknown')
                        features = model_package.get('features', [])
                        trained_at = model_package.get('trained_at', 'unknown')
                        
                        print(f"  - Stored target: {stored_target}")
                        print(f"  - Version: {version}")
                        print(f"  - Features: {len(features)}")
                        print(f"  - Trained: {trained_at}")
                        
                        # Validate target binding
                        if stored_target != target:
                            print(f"  🚨 CRITICAL: Target mismatch! File is for '{stored_target}' not '{target}'")
                            results['issues_found'].append(f"Target mismatch in {target} model")
                        else:
                            print(f"  ✓ Target binding verified")
                        
                        results['feature_analysis'][target] = {
                            'features': features,
                            'stored_target': stored_target,
                            'version': version,
                        }
                    else:
                        # Legacy format
                        print(f"  ⚠️  Legacy model format (no metadata)")
                        results['feature_analysis'][target] = {'features': [], 'stored_target': 'unknown'}
                        
                except Exception as e:
                    print(f"  🚨 Error loading model: {e}")
                    results['issues_found'].append(f"Error loading {target} model: {e}")
            else:
                print(f"✗ Missing {target} model: {filepath}")
                results['models_found'][target] = False
        
        # Check 2: Metrics file
        print("\n" + "=" * 70)
        print("CHECK 2: MODEL METRICS")
        print("=" * 70)
        
        metrics_path = self.models_dir / 'metrics.joblib'
        if metrics_path.exists():
            try:
                metrics = joblib.load(metrics_path)
                print(f"✓ Found metrics file\n")
                
                for target, m in metrics.items():
                    print(f"{target.capitalize()}:")
                    print(f"  MAE:  {m.get('mae', 'N/A')}")
                    print(f"  RMSE: {m.get('rmse', 'N/A')}")
                    print(f"  R²:   {m.get('r2', 'N/A')}")
                    
                    # Check if metrics are reasonable
                    mae = m.get('mae', 0)
                    if target == 'points' and mae > 8:
                        print(f"  ⚠️  Points MAE ({mae}) seems high (expect < 8)")
                    elif target == 'rebounds' and mae > 3:
                        print(f"  ⚠️  Rebounds MAE ({mae}) seems high (expect < 3)")
                    elif target == 'assists' and mae > 2.5:
                        print(f"  ⚠️  Assists MAE ({mae}) seems high (expect < 2.5)")
                    
                    print()
            except Exception as e:
                print(f"🚨 Error loading metrics: {e}")
        else:
            print("✗ No metrics file found")
        
        # Check 3: Feature analysis
        print("\n" + "=" * 70)
        print("CHECK 3: FEATURE ANALYSIS")
        print("=" * 70)
        
        for target, analysis in results['feature_analysis'].items():
            features = analysis.get('features', [])
            print(f"\n{target.upper()} model features ({len(features)} total):")
            
            if not features:
                print("  No features stored (legacy model)")
                continue
            
            # Check for potential leakage
            for feature in features:
                # Check if feature contains a different target name (without being a rolling avg)
                for other_target in self.targets:
                    if other_target != target and other_target in feature:
                        # Rolling avgs of other stats are acceptable
                        if any(x in feature for x in ['avg', 'season', 'rolling']):
                            print(f"  ⚠️  {feature} (contains '{other_target}' - verify this is historical only)")
                        else:
                            print(f"  🚨 {feature} (SUSPICIOUS - contains '{other_target}')")
                            results['issues_found'].append(f"Potential leakage: {feature} in {target} model")
                
                # Check if feature is the target itself
                if feature == target:
                    print(f"  🚨 {feature} (CRITICAL - same as target!)")
                    results['issues_found'].append(f"Target used as feature in {target} model")
            
            # List first 10 features
            for i, f in enumerate(features[:10]):
                print(f"  {i+1}. {f}")
            if len(features) > 10:
                print(f"  ... and {len(features) - 10} more")
        
        # Check 4: Summary
        print("\n" + "=" * 70)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 70)
        
        if results['issues_found']:
            print(f"\n🚨 Found {len(results['issues_found'])} issue(s):")
            for issue in results['issues_found']:
                print(f"  - {issue}")
            print("\nRecommendation: Retrain models with the new SafePerformancePredictor")
        else:
            print("\n✓ No critical issues found")
            
            # Check if models are trained
            all_models_exist = all(results['models_found'].values())
            if not all_models_exist:
                print("\n⚠️  Some models are missing. Run seed_data.py to train models.")
            else:
                print("\n✓ All models present and properly configured")
        
        return results


def main():
    """Run diagnostic."""
    diagnostic = ModelDiagnostic(models_dir='models')
    results = diagnostic.run_full_diagnostic()
    
    # Return exit code based on issues
    if results['issues_found']:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
