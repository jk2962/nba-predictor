/**
 * NBA Player Performance Prediction - API Service
 */
import axios from 'axios';
import type {
    Player,
    PlayerDetail,
    PlayerSearchResult,
    GameStats,
    PredictionResult,
    TopPerformer,
    PaginatedResponse,
    BatchPredictionResponse,
    AllModelMetrics,
} from '../types';

// Create axios instance
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '',
    timeout: 60000, // 60 seconds to handle Render cold starts
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for logging
api.interceptors.request.use((config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API Error]', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

/**
 * Player API endpoints
 */
export const playerApi = {
    /**
     * Get paginated list of players with advanced filtering
     */
    getPlayers: async (params: {
        page?: number;
        per_page?: number;
        search?: string;
        position?: string;
        team?: string;
        ppg_min?: number;
        ppg_max?: number;
        rpg_min?: number;
        rpg_max?: number;
        apg_min?: number;
        apg_max?: number;
        mpg_min?: number;
        mpg_max?: number;
        sort_by?: 'name' | 'ppg' | 'rpg' | 'apg' | 'mpg' | 'fantasy';
        sort_order?: 'asc' | 'desc';
    } = {}): Promise<PaginatedResponse<Player>> => {
        const { data } = await api.get('/api/players', { params });
        return data;
    },

    /**
     * Get list of all NBA teams
     */
    getTeams: async (): Promise<{ name: string; abbreviation: string }[]> => {
        const { data } = await api.get('/api/players/teams');
        return data;
    },

    /**
     * Search players by name
     */
    searchPlayers: async (query: string, limit = 10): Promise<PlayerSearchResult[]> => {
        const { data } = await api.get('/api/players/search', {
            params: { q: query, limit },
        });
        return data;
    },

    /**
     * Get player details by ID
     */
    getPlayer: async (playerId: number): Promise<PlayerDetail> => {
        const { data } = await api.get(`/api/players/${playerId}`);
        return data;
    },

    /**
     * Get player's recent games
     */
    getPlayerGames: async (playerId: number, limit = 10): Promise<GameStats[]> => {
        const { data } = await api.get(`/api/players/${playerId}/games`, {
            params: { limit },
        });
        return data;
    },

    /**
     * Get player predictions
     */
    getPlayerPredictions: async (
        playerId: number,
        params: {
            game_date?: string;
            is_home?: boolean;
            opponent?: string;
        } = {}
    ): Promise<PredictionResult> => {
        const { data } = await api.get(`/api/players/${playerId}/predictions`, { params });
        return data;
    },

    /**
     * Get top performers
     */
    getTopPerformers: async (params: {
        limit?: number;
        stat?: 'points' | 'rebounds' | 'assists' | 'fantasy';
    } = {}): Promise<TopPerformer[]> => {
        const { data } = await api.get('/api/players/top-performers', { params });
        return data;
    },

    /**
     * Get batch predictions for multiple players
     */
    getBatchPredictions: async (
        playerIds: number[],
        gameDate?: string
    ): Promise<BatchPredictionResponse> => {
        const { data } = await api.post('/api/players/predictions/batch', {
            player_ids: playerIds,
            game_date: gameDate,
        });
        return data;
    },

    /**
     * Compare multiple players side-by-side
     */
    comparePlayers: async (playerNames: string[]): Promise<any> => {
        const { data } = await api.post('/api/compare', {
            players: playerNames,
        });
        return data;
    },

    /**
     * Search for player names for comparison
     */
    searchPlayerNames: async (query: string): Promise<{ query: string; results: string[] }> => {
        const { data } = await api.get('/api/compare/search', {
            params: { q: query },
        });
        return data;
    },
};

/**
 * Draft Helper API endpoints
 */
export const draftApi = {
    /**
     * Get full draft rankings with VOR
     */
    getDraftRankings: async (leagueSize = 12, showInactive = false): Promise<any> => {
        const { data } = await api.get('/api/draft/rankings', {
            params: {
                league_size: leagueSize,
                include_inactive: showInactive
            },
        });
        return data;
    },

    /**
     * Get draft recommendation
     */
    getDraftRecommendation: async (
        draftedPlayers: string[],
        myTeam: string[] = [],
        teamNeeds?: { [position: string]: number }
    ): Promise<any> => {
        const { data } = await api.post('/api/draft/recommend', {
            drafted_players: draftedPlayers,
            my_team: myTeam,
            team_needs: teamNeeds,
        });
        return data;
    },

    /**
     * Get positional scarcity analysis
     */
    getScarcity: async (draftedPlayers: string[] = []): Promise<any> => {
        const { data } = await api.get('/api/draft/scarcity', {
            params: { drafted: draftedPlayers.join(',') },
        });
        return data;
    },

    /**
     * Get top N players
     */
    getTopPlayers: async (n: number, position?: string): Promise<any> => {
        const { data } = await api.get(`/api/draft/top/${n}`, {
            params: position ? { position } : {},
        });
        return data;
    },

    /**
     * Export rankings as CSV
     */
    exportRankings: async (): Promise<void> => {
        const response = await api.get('/api/draft/export', {
            responseType: 'blob',
        });

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'fantasy_rankings.csv');
        document.body.appendChild(link);
        link.click();
        link.remove();
    },
};

/**
 * Metrics API endpoints
 */
export const metricsApi = {
    /**
     * Get model metrics
     */
    getMetrics: async (): Promise<AllModelMetrics> => {
        const { data } = await api.get('/api/metrics');
        return data;
    },
};

export default api;
