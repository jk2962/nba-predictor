/**
 * NBA Player Performance Prediction - TypeScript Types
 */

// Player types
export interface Player {
    id: number;
    nba_id: number;
    name: string;
    team: string | null;
    team_abbreviation: string | null;
    position: string | null;
    headshot_url: string | null;
    is_active: boolean;
    season_ppg: number | null;
    season_rpg: number | null;
    season_apg: number | null;
}

export interface PlayerDetail extends Player {
    height: string | null;
    weight: string | null;
    games_played: number;
    season_spg: number | null;
    season_bpg: number | null;
    season_fg_pct: number | null;
    season_fg3_pct: number | null;
    season_ft_pct: number | null;
    season_mpg: number | null;
}

export interface PlayerSearchResult {
    id: number;
    nba_id: number;
    name: string;
    team: string | null;
    team_abbreviation: string | null;
    position: string | null;
    headshot_url: string | null;
}

// Game stats types
export interface GameStats {
    id: number;
    player_id: number;
    game_date: string;
    opponent_team: string | null;
    opponent_abbreviation: string | null;
    is_home: boolean;
    minutes: number;
    points: number;
    rebounds: number;
    assists: number;
    steals: number;
    blocks: number;
    turnovers: number;
    fg_pct: number;
    fg3_pct: number;
    ft_pct: number;
}

// Prediction types
export interface PredictionResult {
    player_id: number;
    player_name: string | null;
    game_date: string;
    opponent_team: string | null;
    is_home: boolean;
    predicted_points: number;
    predicted_rebounds: number;
    predicted_assists: number;
    points_lower: number;
    points_upper: number;
    rebounds_lower: number;
    rebounds_upper: number;
    assists_lower: number;
    assists_upper: number;
    fantasy_score: number | null;
}

export interface TopPerformer {
    player_id: number;
    player_name: string;
    team: string | null;
    team_abbreviation: string | null;
    position: string | null;
    headshot_url: string | null;
    predicted_points: number;
    predicted_rebounds: number;
    predicted_assists: number;
    fantasy_score: number;
    opponent_team: string | null;
    is_home: boolean;
}

// Model metrics types
export interface ModelMetrics {
    model_name: string;
    mae: number;
    rmse: number;
    r2: number;
    last_trained: string | null;
    training_samples: number;
}

export interface AllModelMetrics {
    points_model: ModelMetrics;
    rebounds_model: ModelMetrics;
    assists_model: ModelMetrics;
}

// API response types
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
}

export interface BatchPredictionResponse {
    predictions: PredictionResult[];
    generated_at: string;
}
