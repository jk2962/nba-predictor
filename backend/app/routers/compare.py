"""
Player Comparison Router - FastAPI Endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import logging

from app.ml.predictor import SafePerformancePredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compare", tags=["compare"])

# Initialize predictor (singleton)
predictor = SafePerformancePredictor()

# Load player data
try:
    player_data = pd.read_csv('data/full_nba_game_logs.csv')
    player_data['game_date'] = pd.to_datetime(player_data['game_date'])
    player_data = player_data.sort_values(['player_id', 'game_date'])
except Exception as e:
    logger.error(f"Failed to load player data: {e}")
    player_data = pd.DataFrame()


class ComparisonRequest(BaseModel):
    """Request model for player comparison"""
    players: List[str]


def compare_players_backend(player_names: List[str]) -> dict:
    """Compare multiple players using predictor"""
    
    if len(player_names) < 2:
        return {'error': 'Need at least 2 players'}
    if len(player_names) > 3:
        return {'error': 'Maximum 3 players'}
    
    comparison = {'players': {}, 'summary': {}}
    
    for player_name in player_names:
        # Find player games
        player_games = player_data[
            player_data['player_name'].str.lower() == player_name.lower()
        ]
        
        if len(player_games) == 0:
            comparison['players'][player_name] = {'error': 'Player not found'}
            continue
        
        # Get stats
        last_5 = player_games.tail(5)
        latest = player_games.iloc[-1]
        
        # Make predictions
        try:
            predictions = predictor.predict(
                player_games,
                position=latest.get('position', 'G'),
                is_home=int(latest.get('is_home', 1)),
                opponent_def_rating=float(latest.get('opponent_def_rating', 110.0)),
                rest_days=int(latest.get('rest_days', 2))
            )
        except Exception as e:
            logger.error(f"Prediction failed for {player_name}: {e}")
            predictions = {}
        
        comparison['players'][player_name] = {
            'name': latest.get('player_name', player_name),
            'predictions': predictions,
            'season_avg': {
                'points': round(player_games['points'].mean(), 1),
                'rebounds': round(player_games['rebounds'].mean(), 1),
                'assists': round(player_games['assists'].mean(), 1),
            },
            'last_5_avg': {
                'points': round(last_5['points'].mean(), 1),
                'rebounds': round(last_5['rebounds'].mean(), 1),
                'assists': round(last_5['assists'].mean(), 1),
            },
            'matchup': {
                'opponent': latest.get('opponent', 'N/A'),
                'location': 'Home' if latest.get('is_home', 1) == 1 else 'Away',
            },
            'games_played': len(player_games)
        }
    
    # Calculate head-to-head winners
    for stat in ['points', 'rebounds', 'assists']:
        values = {}
        for player, data in comparison['players'].items():
            if 'error' in data:
                continue
            pred_data = data.get('predictions', {}).get(stat)
            if pred_data and isinstance(pred_data, dict):
                # Extract 'predicted' value from dict
                values[player] = pred_data.get('predicted')
            elif pred_data is not None:
                values[player] = pred_data
        
        if values:
            winner = max(values, key=values.get)
            comparison['summary'][f'{stat}_winner'] = winner
    
    return comparison


@router.post("")
async def compare_players(request: ComparisonRequest):
    """
    Compare 2-3 NBA players.
    
    Returns predictions, season stats, and head-to-head analysis.
    """
    
    if not predictor._models_loaded:
        predictor.load_models()
    
    result = compare_players_backend(request.players)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.get("/simple")
async def compare_players_simple(
    player1: str = Query(..., description="First player name"),
    player2: str = Query(..., description="Second player name"),
    player3: Optional[str] = Query(None, description="Third player name (optional)")
):
    """
    Simple GET endpoint for comparison.
    
    Example: /api/compare/simple?player1=Trae Young&player2=Luka Doncic
    """
    
    if not predictor._models_loaded:
        predictor.load_models()
    
    players = [player1, player2]
    if player3:
        players.append(player3)
    
    result = compare_players_backend(players)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.get("/search")
async def search_players(q: str = Query(..., min_length=2, description="Search query")):
    """
    Search for players by name.
    
    Example: /api/compare/search?q=tra
    """
    
    query_lower = q.lower()
    
    matching = player_data[
        player_data['player_name'].str.lower().str.contains(query_lower, na=False)
    ]['player_name'].unique().tolist()
    
    return {
        'query': q,
        'results': matching[:10]
    }
