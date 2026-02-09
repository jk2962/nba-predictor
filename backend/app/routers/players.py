"""
NBA Player Performance Prediction - Players API Router
"""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models import Player, Game
from app.schemas import (
    PlayerListItem, PlayerDetail, GameStats, PredictionResult,
    TopPerformer, BatchPredictionRequest, BatchPredictionResponse,
    PaginatedResponse, PlayerSearchResult, AllModelMetrics, ModelMetrics
)
from app.services import PlayerService, prediction_cache
from app.ml import predictor
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("", response_model=PaginatedResponse)
async def list_players(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by player name, team"),
    position: Optional[str] = Query(None, description="Filter by position (comma-separated: PG,SG,SF,PF,C)"),
    team: Optional[str] = Query(None, description="Filter by team abbreviation (comma-separated: LAL,GSW)"),
    # Stat range filters
    ppg_min: Optional[float] = Query(None, ge=0, description="Minimum PPG"),
    ppg_max: Optional[float] = Query(None, ge=0, description="Maximum PPG"),
    rpg_min: Optional[float] = Query(None, ge=0, description="Minimum RPG"),
    rpg_max: Optional[float] = Query(None, ge=0, description="Maximum RPG"),
    apg_min: Optional[float] = Query(None, ge=0, description="Minimum APG"),
    apg_max: Optional[float] = Query(None, ge=0, description="Maximum APG"),
    mpg_min: Optional[float] = Query(None, ge=0, description="Minimum MPG"),
    mpg_max: Optional[float] = Query(None, ge=0, description="Maximum MPG"),
    # Sorting
    sort_by: str = Query("fantasy", description="Sort by: name, ppg, rpg, apg, mpg, fantasy"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of active NBA players with advanced filtering.
    
    Supports filtering by name, position, team, and stat ranges.
    Results include calculated fantasy score.
    """
    skip = (page - 1) * per_page
    players_data, total = PlayerService.get_players(
        db, 
        skip=skip, 
        limit=per_page, 
        search=search, 
        position=position, 
        team=team,
        ppg_min=ppg_min,
        ppg_max=ppg_max,
        rpg_min=rpg_min,
        rpg_max=rpg_max,
        apg_min=apg_min,
        apg_max=apg_max,
        mpg_min=mpg_min,
        mpg_max=mpg_max,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    # Build response items (stats are already included)
    items = []
    for data in players_data:
        player = data['player']
        items.append(PlayerListItem(
            id=player.id,
            nba_id=player.nba_id,
            name=player.name,
            team=player.team,
            team_abbreviation=player.team_abbreviation,
            position=player.position,
            headshot_url=player.headshot_url,
            is_active=player.is_active,
            season_ppg=data['ppg'],
            season_rpg=data['rpg'],
            season_apg=data['apg'],
            season_mpg=data.get('mpg'),
            fantasy_score=data.get('fantasy'),
        ))
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/search", response_model=List[PlayerSearchResult])
async def search_players(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Quick search for players by name.
    
    Returns simplified results for autocomplete.
    """
    players_data, _ = PlayerService.get_players(db, limit=limit, search=q)
    
    return [
        PlayerSearchResult(
            id=data['player'].id,
            nba_id=data['player'].nba_id,
            name=data['player'].name,
            team=data['player'].team,
            team_abbreviation=data['player'].team_abbreviation,
            position=data['player'].position,
            headshot_url=data['player'].headshot_url,
        )
        for data in players_data
    ]


@router.get("/teams", response_model=List[dict])
async def get_teams(db: Session = Depends(get_db)):
    """
    Get list of all NBA teams.
    
    Returns team names and abbreviations for filter dropdowns.
    """
    return PlayerService.get_all_teams(db)


@router.get("/top-performers", response_model=List[TopPerformer])
async def get_top_performers(
    limit: int = Query(10, ge=1, le=50, description="Number of top performers"),
    stat: str = Query("fantasy", description="Sort by: points, rebounds, assists, fantasy"),
    db: Session = Depends(get_db)
):
    """
    Get the top predicted performers for the next games.
    
    Fantasy score is calculated as: PTS + 1.2*REB + 1.5*AST
    """
    # Check cache
    cache_key = f"top_performers:{limit}:{stat}"
    cached = prediction_cache.get(cache_key)
    if cached:
        return cached
    
    # Get all active players with stats
    players_data = PlayerService.get_all_players_for_ranking(db)
    
    performers = []
    for player_data in players_data:
        # Get stats dataframe for prediction
        stats_df = PlayerService.get_player_stats_dataframe(db, player_data['id'])
        
        if stats_df.empty or len(stats_df) < 5:
            continue
        
        # Make prediction with position for realistic bounds
        predictions = predictor.predict(stats_df, position=player_data.get('position'))
        
        if not predictions:
            continue
        
        pts = predictions.get('points', {}).get('predicted', 0)
        reb = predictions.get('rebounds', {}).get('predicted', 0)
        ast = predictions.get('assists', {}).get('predicted', 0)
        
        # Get defensive stats from season averages (not predicted)
        stl = stats_df['steals'].mean() if 'steals' in stats_df.columns else 0
        blk = stats_df['blocks'].mean() if 'blocks' in stats_df.columns else 0
        tov = stats_df['turnovers'].mean() if 'turnovers' in stats_df.columns else 0
        
        # Fantasy score formula: PTS + 1.2*REB + 1.5*AST + 3*STL + 3*BLK - 1*TO
        fantasy_score = pts + 1.2 * reb + 1.5 * ast + 3.0 * stl + 3.0 * blk - 1.0 * tov
        
        performers.append(TopPerformer(
            player_id=player_data['id'],
            player_name=player_data['name'],
            team=player_data.get('team'),
            team_abbreviation=player_data.get('team_abbreviation'),
            position=player_data.get('position'),
            headshot_url=player_data.get('headshot_url'),
            predicted_points=pts,
            predicted_rebounds=reb,
            predicted_assists=ast,
            fantasy_score=round(fantasy_score, 1)
        ))
    
    # Sort by requested stat
    if stat == "points":
        performers.sort(key=lambda x: x.predicted_points, reverse=True)
    elif stat == "rebounds":
        performers.sort(key=lambda x: x.predicted_rebounds, reverse=True)
    elif stat == "assists":
        performers.sort(key=lambda x: x.predicted_assists, reverse=True)
    else:  # fantasy
        performers.sort(key=lambda x: x.fantasy_score, reverse=True)
    
    result = performers[:limit]
    
    # Cache the result
    prediction_cache.set(cache_key, result)
    
    return result


@router.get("/{player_id}", response_model=PlayerDetail)
async def get_player(
    player_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific player.
    
    Includes season averages and basic stats.
    """
    player = PlayerService.get_player_by_id(db, player_id)
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    stats = PlayerService.get_player_season_stats(db, player_id)
    
    return PlayerDetail(
        id=player.id,
        nba_id=player.nba_id,
        name=player.name,
        team=player.team,
        team_abbreviation=player.team_abbreviation,
        position=player.position,
        height=player.height,
        weight=player.weight,
        headshot_url=player.headshot_url,
        is_active=player.is_active,
        games_played=stats.get('games_played', 0),
        season_ppg=stats.get('ppg'),
        season_rpg=stats.get('rpg'),
        season_apg=stats.get('apg'),
        season_spg=stats.get('spg'),
        season_bpg=stats.get('bpg'),
        season_mpg=stats.get('mpg'),
        season_fg_pct=stats.get('fg_pct'),
        season_fg3_pct=stats.get('fg3_pct'),
        season_ft_pct=stats.get('ft_pct'),
    )


@router.get("/{player_id}/games", response_model=List[GameStats])
async def get_player_games(
    player_id: int,
    limit: int = Query(10, ge=1, le=82, description="Number of recent games"),
    db: Session = Depends(get_db)
):
    """
    Get a player's recent game stats.
    
    Returns the most recent games first.
    """
    player = PlayerService.get_player_by_id(db, player_id)
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    games = PlayerService.get_player_recent_games(db, player_id, limit=limit)
    
    result = []
    for stat in games:
        game = stat.game
        result.append(GameStats(
            id=stat.id,
            player_id=stat.player_id,
            game_date=game.game_date,
            opponent_team=stat.opponent_team,
            opponent_abbreviation=stat.opponent_abbreviation,
            is_home=stat.is_home,
            minutes=stat.minutes,
            points=stat.points,
            rebounds=stat.rebounds,
            assists=stat.assists,
            steals=stat.steals,
            blocks=stat.blocks,
            turnovers=stat.turnovers,
            fg_pct=stat.fg_pct,
            fg3_pct=stat.fg3_pct,
            ft_pct=stat.ft_pct,
        ))
    
    return result


@router.get("/{player_id}/predictions", response_model=PredictionResult)
async def get_player_predictions(
    player_id: int,
    game_date: Optional[date] = Query(None, description="Target game date"),
    is_home: bool = Query(True, description="Is home game"),
    opponent: Optional[str] = Query(None, description="Opponent team abbreviation"),
    db: Session = Depends(get_db)
):
    """
    Get performance predictions for a player's next game.
    
    Returns predicted points, rebounds, assists with confidence intervals.
    """
    player = PlayerService.get_player_by_id(db, player_id)
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check cache
    cache_key = f"prediction:{player_id}:{game_date}:{is_home}:{opponent}"
    cached = prediction_cache.get(cache_key)
    if cached:
        return cached
    
    # Get player stats for prediction
    stats_df = PlayerService.get_player_stats_dataframe(db, player_id)
    
    if stats_df.empty:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient data for prediction"
        )
    
    # Make prediction with position bounds
    predictions = predictor.predict(
        stats_df,
        position=player.position,
        game_date=game_date,
        is_home=is_home
    )
    
    if not predictions:
        raise HTTPException(
            status_code=500, 
            detail="Prediction failed. Model may not be trained."
        )
    
    pts = predictions.get('points', {})
    reb = predictions.get('rebounds', {})
    ast = predictions.get('assists', {})
    
    # Calculate fantasy score including defensive stats
    stl = stats_df['steals'].mean() if 'steals' in stats_df.columns else 0
    blk = stats_df['blocks'].mean() if 'blocks' in stats_df.columns else 0
    tov = stats_df['turnovers'].mean() if 'turnovers' in stats_df.columns else 0
    
    # Fantasy score: PTS + 1.2*REB + 1.5*AST + 3*STL + 3*BLK - 1*TO
    fantasy = (
        pts.get('predicted', 0) + 
        1.2 * reb.get('predicted', 0) + 
        1.5 * ast.get('predicted', 0) +
        3.0 * stl + 3.0 * blk - 1.0 * tov
    )
    
    result = PredictionResult(
        player_id=player_id,
        player_name=player.name,
        game_date=game_date or date.today(),
        opponent_team=opponent,
        is_home=is_home,
        predicted_points=pts.get('predicted', 0),
        predicted_rebounds=reb.get('predicted', 0),
        predicted_assists=ast.get('predicted', 0),
        points_lower=pts.get('lower', 0),
        points_upper=pts.get('upper', 0),
        rebounds_lower=reb.get('lower', 0),
        rebounds_upper=reb.get('upper', 0),
        assists_lower=ast.get('lower', 0),
        assists_upper=ast.get('upper', 0),
        fantasy_score=round(fantasy, 1)
    )
    
    # Cache the result
    prediction_cache.set(cache_key, result)
    
    return result


@router.post("/predictions/batch", response_model=BatchPredictionResponse)
async def get_batch_predictions(
    request: BatchPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Get predictions for multiple players at once.
    
    Useful for comparison views and draft tools.
    """
    predictions = []
    
    for player_id in request.player_ids:
        player = PlayerService.get_player_by_id(db, player_id)
        
        if not player:
            continue
        
        stats_df = PlayerService.get_player_stats_dataframe(db, player_id)
        
        if stats_df.empty:
            continue
        
        pred = predictor.predict(
            stats_df, 
            position=player.position,
            game_date=request.game_date
        )
        
        if not pred:
            continue
        
        pts = pred.get('points', {})
        reb = pred.get('rebounds', {})
        ast = pred.get('assists', {})
        
        # Get defensive stats from season averages
        stl = stats_df['steals'].mean() if 'steals' in stats_df.columns else 0
        blk = stats_df['blocks'].mean() if 'blocks' in stats_df.columns else 0
        tov = stats_df['turnovers'].mean() if 'turnovers' in stats_df.columns else 0
        
        # Fantasy score: PTS + 1.2*REB + 1.5*AST + 3*STL + 3*BLK - 1*TO
        fantasy = (
            pts.get('predicted', 0) + 
            1.2 * reb.get('predicted', 0) + 
            1.5 * ast.get('predicted', 0) +
            3.0 * stl + 3.0 * blk - 1.0 * tov
        )
        
        predictions.append(PredictionResult(
            player_id=player_id,
            player_name=player.name,
            game_date=request.game_date or date.today(),
            is_home=True,
            predicted_points=pts.get('predicted', 0),
            predicted_rebounds=reb.get('predicted', 0),
            predicted_assists=ast.get('predicted', 0),
            points_lower=pts.get('lower', 0),
            points_upper=pts.get('upper', 0),
            rebounds_lower=reb.get('lower', 0),
            rebounds_upper=reb.get('upper', 0),
            assists_lower=ast.get('lower', 0),
            assists_upper=ast.get('upper', 0),
            fantasy_score=round(fantasy, 1)
        ))
    
    return BatchPredictionResponse(
        predictions=predictions,
        generated_at=datetime.utcnow()
    )


# Additional router for model metrics
metrics_router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@metrics_router.get("", response_model=AllModelMetrics)
async def get_model_metrics():
    """
    Get evaluation metrics for all trained models.
    
    Shows MAE, RMSE, and R² for points, rebounds, and assists models.
    """
    metrics = predictor.get_metrics()
    
    def get_metric(target: str) -> ModelMetrics:
        m = metrics.get(target, {})
        return ModelMetrics(
            model_name=f"{target}_model",
            mae=m.get('mae', 0),
            rmse=m.get('rmse', 0),
            r2=m.get('r2', 0),
            last_trained=datetime.fromisoformat(m['last_trained']) if m.get('last_trained') else None,
            training_samples=m.get('training_samples', 0)
        )
    
    return AllModelMetrics(
        points_model=get_metric('points'),
        rebounds_model=get_metric('rebounds'),
        assists_model=get_metric('assists')
    )
