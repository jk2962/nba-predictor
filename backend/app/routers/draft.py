"""
Draft Helper Router - FastAPI Endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging

from app.ml.draft_helper import get_draft_helper



logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/draft", tags=["draft"])

# Get draft helper singleton
draft_helper = get_draft_helper()


# --- Request/Response Models ---

class DraftRecommendationRequest(BaseModel):
    """Request for draft recommendation"""
    drafted_players: List[str]
    my_team: Optional[List[str]] = []
    team_needs: Optional[Dict[str, int]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "drafted_players": ["LeBron James", "Stephen Curry"],
                "my_team": ["LeBron James"],
                "team_needs": {"G": 1, "C": 1}
            }
        }


# --- Endpoints ---

@router.get("/rankings")
async def get_draft_rankings(
    league_size: int = Query(12, description="League size (default: 12)"),
    scoring: Optional[str] = Query(None, description="Scoring system (e.g. 'points', 'categories')"),
    include_inactive: bool = Query(False, description="Include inactive players (6m+ no games)")
):
    """
    Get player rankings for fantasy draft.
    
    By default, excludes players who haven't played in 6+ months.
    Set include_inactive=true to see everyone.
    """
    try:
        # Generate rankings
        rankings = draft_helper.rank_all_players(
            league_size=league_size,
            include_inactive=include_inactive
        )
        
        # Convert to list of dicts
        return {
            'total_players': len(rankings),
            'league_size': league_size,
            'includes_inactive': include_inactive,
            'rankings': rankings.to_dict('records')
        }
    except Exception as e:
        logger.error(f"Failed to get rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/{n}")
async def get_top_n_players(
    n: int,
    position: Optional[str] = Query(None, description="Filter by position (G, F, C)")
):
    """
    Get top N players overall or by position.
    
    Example: /api/draft/top/50
    Example: /api/draft/top/20?position=G
    """
    
    try:
        rankings = draft_helper.rank_all_players()
        
        if position:
            rankings = rankings[rankings['position'] == position.upper()]
        
        top_n = rankings.head(n)
        
        return {
            'requested': n,
            'position_filter': position,
            'returned': len(top_n),
            'players': top_n.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to get top {n}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend")
async def get_draft_recommendation(request: DraftRecommendationRequest):
    """
    Get personalized draft recommendation.
    
    Considers:
    - Who's already been drafted
    - Your current team
    - Your team's positional needs
    
    Returns best player to draft next.
    """
    
    try:
        # Get rankings
        rankings = draft_helper.rank_all_players()
        
        # Get recommendation
        recommendation = draft_helper.get_draft_recommendation(
            rankings=rankings,
            drafted_players=request.drafted_players,
            my_team=request.my_team,
            team_needs=request.team_needs
        )
        
        if 'error' in recommendation:
            raise HTTPException(status_code=404, detail=recommendation['error'])
        
        return recommendation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/available")
async def get_best_available(
    drafted_players: List[str] = [],
    top_n: int = Query(10, description="Number of players to return")
):
    """
    Get best available players (not yet drafted).
    
    Example request body:
    {
        "drafted_players": ["LeBron James", "Stephen Curry"]
    }
    """
    
    try:
        rankings = draft_helper.rank_all_players()
        
        available = draft_helper.get_best_available(
            rankings=rankings,
            drafted_players=drafted_players,
            top_n=top_n
        )
        
        return {
            'total_drafted': len(drafted_players),
            'total_available': len(rankings) - len(drafted_players),
            'top_n_requested': top_n,
            'players': available.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to get available: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scarcity")
async def get_positional_scarcity(
    drafted: Optional[str] = Query(None, description="Comma-separated list of drafted players")
):
    """
    Analyze positional scarcity.
    
    Shows which positions are running out of quality players.
    
    Example: /api/draft/scarcity?drafted=LeBron James,Stephen Curry
    """
    
    try:
        drafted_players = []
        if drafted:
            drafted_players = [p.strip() for p in drafted.split(',')]
        
        rankings = draft_helper.rank_all_players()
        
        scarcity = draft_helper.analyze_positional_scarcity(
            rankings=rankings,
            drafted_players=drafted_players
        )
        
        return {
            'total_drafted': len(drafted_players),
            'scarcity_by_position': scarcity
        }
        
    except Exception as e:
        logger.error(f"Failed to get scarcity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/{player_name}/adp")
async def get_player_adp(player_name: str):
    """
    Get Average Draft Position (ADP) for a specific player.
    
    Shows where this player is typically drafted.
    """
    
    try:
        rankings = draft_helper.rank_all_players()
        
        player_data = rankings[rankings['player_name'].str.lower() == player_name.lower()]
        
        if len(player_data) == 0:
            raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")
        
        player = player_data.iloc[0]
        
        return {
            'player_name': player['player_name'],
            'position': player['position'],
            'overall_rank': int(player['rank']),
            'position_rank': int(player['position_rank']),
            'fantasy_points': float(player['fantasy_points']),
            'vor': float(player['vor']),
            'typical_round': (int(player['rank']) - 1) // 12 + 1,  # 12-team league
            'projections': {
                'points': float(player['proj_points']),
                'rebounds': float(player['proj_rebounds']),
                'assists': float(player['proj_assists'])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ADP for {player_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_rankings_csv():
    """
    Export rankings to CSV.
    """
    try:
        from fastapi.responses import StreamingResponse
        import io
        import pandas as pd
        
        rankings = draft_helper.rank_all_players()
        
        # Select and rename columns for export
        export_df = rankings[[
            'rank', 'player_name', 'position', 'fantasy_points', 'vor',
            'proj_points', 'proj_rebounds', 'proj_assists', 
            'proj_steals', 'proj_blocks', 'proj_turnovers'
        ]].copy()
        
        export_df.columns = [
            'Rank', 'Player', 'Position', 'Fantasy Pts', 'VOR',
            'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO'
        ]
        
        # Create CSV in memory
        stream = io.StringIO()
        export_df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=fantasy_rankings.csv"
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to export rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
